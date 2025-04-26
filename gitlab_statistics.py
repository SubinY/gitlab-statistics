import gitlab
import pandas as pd
from datetime import datetime
import os
from collections import defaultdict
import re
import sys
import math

# 尝试导入配置文件
try:
    import config
    # 检查配置文件是否包含必要的参数
    if not hasattr(config, 'GITLAB_URL') or not hasattr(config, 'GITLAB_TOKEN'):
        print("错误: 配置文件中缺少 GITLAB_URL 或 GITLAB_TOKEN 参数")
        print("请确保您已正确设置 config.py 文件")
        sys.exit(1)
except ImportError:
    print("错误: 找不到配置文件 (config.py)")
    print("请创建配置文件，可以复制 config.template.py 为 config.py 并填写相应参数")
    sys.exit(1)

def apply_scale_factor(value, scale_factor):
    """
    应用缩放因子到数值
    
    Args:
        value (int): 原始数值
        scale_factor (float): 缩放因子
        
    Returns:
        int: 缩放后的数值，不小于0的整数
    """
    if scale_factor == 0 or scale_factor == 1:
        return value
        
    if scale_factor > 0:
        # 正数：乘以系数
        scaled_value = value * scale_factor
    else:
        # 负数：除以系数的绝对值
        scaled_value = value / abs(scale_factor)
        
    # 取整并确保不小于0
    return max(0, int(round(scaled_value)))

def get_user_input():
    """Get user input for parameters"""
    print("=== GitLab 代码统计工具 ===")
    
    # GitLab 连接信息
    default_gitlab_url = config.GITLAB_URL
    default_gitlab_token = config.GITLAB_TOKEN
    gitlab_url = input(f"GitLab URL (默认: {default_gitlab_url}): ") or default_gitlab_url
    gitlab_token = input(f"访问令牌 (默认: 使用配置文件中的令牌): ") or default_gitlab_token
    
    # 日期范围
    default_start_date = getattr(config, 'DEFAULT_START_DATE', "2023-01-01")
    default_end_date = getattr(config, 'DEFAULT_END_DATE', "2023-12-31")
    start_date = input(f"开始日期 (格式: YYYY-MM-DD，默认: {default_start_date}): ") or default_start_date
    end_date = input(f"结束日期 (格式: YYYY-MM-DD，默认: {default_end_date}): ") or default_end_date
    
    # 仓库路径
    default_repos = getattr(config, 'DEFAULT_REPOSITORIES', "")
    print("\n注意: 仓库路径需要是完整路径，格式为 '组名/[子组名]/项目名'")
    print("例如: 'group/subgroup/project-name'")
    print("如果不确定完整路径，可以输入项目的部分名称，系统会自动搜索匹配的项目")
    repos_input = input(f"仓库路径 (用逗号分隔, 默认: {default_repos}): ") or default_repos
    repo_paths = [r.strip() for r in repos_input.split(',')]
    
    # 用户名
    default_users = getattr(config, 'DEFAULT_USERS', "")
    users_input = input(f"用户姓名 (用逗号分隔, 默认: {default_users}): ") or default_users
    user_names = [u.strip() for u in users_input.split(',')]
    
    # 模糊匹配
    default_fuzzy = getattr(config, 'DEFAULT_FUZZY_MATCH', True)
    fuzzy_match = input(f"是否开启用户名模糊匹配 (y/n, 默认: {'y' if default_fuzzy else 'n'}): ")
    if fuzzy_match.lower() in ('y', 'n'):
        fuzzy_match = fuzzy_match.lower() == 'y'
    else:
        fuzzy_match = default_fuzzy
    
    # 最大分支数
    default_max_branches = getattr(config, 'DEFAULT_MAX_BRANCHES', 1)
    max_branches_input = input(f"每个仓库分析的最大活跃分支数 (默认: {default_max_branches}): ")
    max_branches = int(max_branches_input) if max_branches_input.strip() else default_max_branches
    
    # 输出文件名
    default_output_file = getattr(config, 'DEFAULT_OUTPUT_FILE', "gitlab_statistics.xlsx")
    output_file = input(f"输出Excel文件名 (默认: {default_output_file}): ") or default_output_file
    
    # 数据缩放因子
    default_scale = getattr(config, 'SCALE_FACTOR', 1)
    scale_input = input(f"数据缩放因子 (正数乘以，负数除以，默认: {default_scale}): ")
    if scale_input.strip():
        try:
            scale_factor = float(scale_input)
        except ValueError:
            print(f"无效的缩放因子，使用默认值: {default_scale}")
            scale_factor = default_scale
    else:
        scale_factor = default_scale
    
    return {
        "gitlab_url": gitlab_url,
        "gitlab_token": gitlab_token,
        "start_date": start_date,
        "end_date": end_date,
        "repo_paths": repo_paths,
        "user_names": user_names,
        "fuzzy_match": fuzzy_match,
        "max_branches": max_branches,
        "output_file": output_file,
        "scale_factor": scale_factor
    }

def list_available_projects(gl, search_term=None):
    """
    List available projects in GitLab
    
    Args:
        gl (gitlab.Gitlab): GitLab connection
        search_term (str): Optional search term
    """
    try:
        if search_term:
            projects = gl.projects.list(search=search_term)
            print(f"\n===== 搜索 '{search_term}' 的结果 =====")
        else:
            projects = gl.projects.list(all=True)
            print("\n===== 可用的仓库列表 =====")
            
        if not projects:
            print("未找到任何项目")
            return
            
        print("ID\t路径")
        print("-" * 50)
        for project in projects[:30]:  # Only show first 30 to avoid flooding
            print(f"{project.id}\t{project.path_with_namespace}")
            
        if len(projects) > 30:
            print(f"... 还有 {len(projects) - 30} 个项目 ...")
            
        print("-" * 50)
        print(f"共找到 {len(projects)} 个项目")
        print("\n提示: 使用上面显示的完整路径作为仓库路径")
        
    except Exception as e:
        print(f"列出项目时出错: {e}")

def is_name_match(author_name, user_names, fuzzy_match=True):
    """
    Check if author name matches any of the user names
    
    Args:
        author_name (str): Author name from commit
        user_names (list): List of user names to match
        fuzzy_match (bool): Whether to use fuzzy matching
        
    Returns:
        tuple: (bool, str) - (is_match, matched_user_name)
    """
    # 使用配置文件中的用户名映射
    name_mappings = getattr(config, 'USER_NAME_MAPPINGS', {})
    
    # 检查是否在配置的映射中
    if author_name.lower() in name_mappings:
        mapped_name = name_mappings[author_name.lower()]
        if mapped_name in user_names:
            return True, mapped_name
    
    # Exact match
    if author_name in user_names:
        return True, author_name
    
    # Fuzzy match
    if fuzzy_match:
        # Try if author name contains user name or user name contains author name
        for user_name in user_names:
            # Remove spaces for comparison
            clean_author = author_name.replace(' ', '').lower()
            clean_user = user_name.replace(' ', '').lower()
            
            # Case 1: Author name contains user name
            if clean_user in clean_author:
                return True, user_name
                
            # Case 2: User name contains author name
            if clean_author in clean_user:
                return True, user_name
                
            # Case 3: First character match for Chinese names
            if len(clean_user) >= 2 and len(clean_author) >= 2:
                # For Chinese names, often only the last character (given name) is different
                if clean_user[0] == clean_author[0]:  # First character match
                    return True, user_name
    
    return False, None

def get_commit_statistics(gitlab_url, gitlab_token, repo_paths, user_names, start_date, end_date, fuzzy_match=True, max_branches=5):
    """
    Get commit statistics from GitLab repositories
    
    Args:
        gitlab_url (str): GitLab server URL
        gitlab_token (str): GitLab access token
        repo_paths (list): List of repository paths to analyze
        user_names (list): List of user names to track
        start_date (str): Start date in format 'YYYY-MM-DD'
        end_date (str): End date in format 'YYYY-MM-DD'
        fuzzy_match (bool): Whether to use fuzzy matching for user names
        max_branches (int): Maximum number of active branches to analyze
    
    Returns:
        dict: Statistics per user and repository
    """
    # Connect to GitLab
    try:
        gl = gitlab.Gitlab(gitlab_url, private_token=gitlab_token)
        gl.auth()
        print(f"成功连接到 GitLab，当前用户: {gl.user.name}")
    except Exception as e:
        print(f"连接 GitLab 失败: {e}")
        return None
    
    # Convert dates to ISO format for GitLab API
    try:
        start_date_iso = datetime.strptime(start_date, '%Y-%m-%d').isoformat()
        end_date_iso = datetime.strptime(end_date, '%Y-%m-%d').isoformat()
    except ValueError as e:
        print(f"日期格式错误: {e}")
        return None
    
    # List all available projects to help users find correct paths
    print("\n正在获取可用的仓库列表，这可能需要一些时间...")
    list_available_projects(gl)
    
    # Ask if user wants to continue or update repo paths
    update_repos = input("\n要更新仓库路径吗? (y/n，默认: n): ").lower() == 'y'
    if update_repos:
        repos_input = input("请输入新的仓库路径 (用逗号分隔): ")
        repo_paths = [r.strip() for r in repos_input.split(',')]
        print(f"已更新仓库路径: {repo_paths}")
    
    # Initialize statistics dictionary
    stats = {user: {"total_commits": 0, "total_additions": 0, "total_deletions": 0, "repos": {}} for user in user_names}
    
    # Store name mappings for consistent author identification
    name_mappings = {}
    
    # Process each repository
    for repo_path in repo_paths:
        print(f"\n处理仓库: {repo_path}")
        
        # Find the project by path
        try:
            # Remove leading slash if present
            if repo_path.startswith('/'):
                repo_path = repo_path[1:]
                
            # Try exact match first
            project = None
            try:
                # Try to get the project directly by path
                project = gl.projects.get(repo_path)
                print(f"已找到仓库: {project.path_with_namespace} (ID: {project.id})")
            except gitlab.exceptions.GitlabGetError:
                # If direct get fails, search for it
                print(f"直接路径未找到，正在搜索 '{repo_path}'...")
                projects = gl.projects.list(search=repo_path)
                
                if not projects:
                    print(f"未找到匹配 '{repo_path}' 的仓库")
                    
                    # Try to search more broadly if nothing is found
                    parts = repo_path.split('/')
                    if len(parts) > 1:
                        project_name = parts[-1]
                        print(f"尝试搜索项目名 '{project_name}'...")
                        projects = gl.projects.list(search=project_name)
                
                if projects:
                    print(f"搜索结果:")
                    for i, p in enumerate(projects[:10]):
                        print(f"{i+1}. {p.path_with_namespace} (ID: {p.id})")
                    
                    if len(projects) == 1:
                        project = projects[0]
                        print(f"自动选择唯一匹配的项目: {project.path_with_namespace}")
                    else:
                        try:
                            choice = input("请选择项目编号 (输入数字或直接回车跳过): ")
                            if choice.strip():
                                idx = int(choice) - 1
                                if 0 <= idx < len(projects):
                                    project = projects[idx]
                                    print(f"已选择: {project.path_with_namespace}")
                                else:
                                    print("选择无效，跳过此仓库")
                            else:
                                print("未选择，跳过此仓库")
                        except (ValueError, IndexError):
                            print("选择无效，跳过此仓库")
            
            if not project:
                print(f"跳过仓库: {repo_path}")
                continue
            
            # Update repo_path to the actual path_with_namespace
            repo_path = project.path_with_namespace
                
        except Exception as e:
            print(f"查找仓库 {repo_path} 时出错: {e}")
            continue
        
        # Get branches sorted by last activity
        try:
            branches = project.branches.list(all=True)
            # Sort branches by last commit date if available
            active_branches = sorted(branches, key=lambda b: b.commit.get('committed_date', ''), reverse=True)
            
            # Limit to max_branches
            active_branches = active_branches[:max_branches]
            branch_names = [b.name for b in active_branches]
            print(f"分析 {len(branch_names)} 个分支: {', '.join(branch_names)}")
            
        except Exception as e:
            print(f"获取仓库 {repo_path} 的分支时出错: {e}")
            continue
        
        # Initialize repo stats for each user
        for user in user_names:
            stats[user]["repos"][repo_path] = {
                "commits": 0,
                "additions": 0,
                "deletions": 0,
                "branches": {}
            }
        
        # Process each branch
        for branch in active_branches:
            branch_name = branch.name
            print(f"分析分支: {branch_name}")
            
            # Initialize branch stats for each user
            for user in user_names:
                stats[user]["repos"][repo_path]["branches"][branch_name] = {
                    "commits": 0,
                    "additions": 0,
                    "deletions": 0
                }
            
            # Get commits in date range
            try:
                commits = project.commits.list(
                    ref_name=branch_name,
                    since=start_date_iso,
                    until=end_date_iso,
                    all=True
                )
                
                print(f"  找到 {len(commits)} 个提交")
                
                # Process each commit
                unique_authors = set()
                user_commit_count = {user: 0 for user in user_names}
                
                for commit in commits:
                    # Get commit details
                    try:
                        commit_detail = project.commits.get(commit.id)
                        author_name = commit_detail.author_name
                        unique_authors.add(author_name)
                        
                        # Use cached mapping if available
                        if author_name in name_mappings:
                            matched_user = name_mappings[author_name]
                        else:
                            # Check if this is a user we're tracking
                            is_match, matched_user = is_name_match(author_name, user_names, fuzzy_match)
                            # Cache the result
                            name_mappings[author_name] = matched_user
                        
                        if matched_user:
                            user_commit_count[matched_user] += 1
                            # Get commit stats
                            stats[matched_user]["total_commits"] += 1
                            stats[matched_user]["repos"][repo_path]["commits"] += 1
                            stats[matched_user]["repos"][repo_path]["branches"][branch_name]["commits"] += 1
                            
                            # Get line changes
                            additions = commit_detail.stats.get('additions', 0)
                            deletions = commit_detail.stats.get('deletions', 0)
                            
                            # Update statistics
                            stats[matched_user]["total_additions"] += additions
                            stats[matched_user]["total_deletions"] += deletions
                            stats[matched_user]["repos"][repo_path]["additions"] += additions
                            stats[matched_user]["repos"][repo_path]["deletions"] += deletions
                            stats[matched_user]["repos"][repo_path]["branches"][branch_name]["additions"] += additions
                            stats[matched_user]["repos"][repo_path]["branches"][branch_name]["deletions"] += deletions
                            
                    except Exception as e:
                        print(f"处理提交 {commit.id} 时出错: {e}")
                        continue
                
                # Print summary of authors found
                if unique_authors:
                    print(f"  提交作者: {', '.join(unique_authors)}")
                    
                    # Print matched users
                    matched_users = [user for user in user_names if user_commit_count[user] > 0]
                    if matched_users:
                        print(f"  匹配的用户: {', '.join(matched_users)}")
                        for user in matched_users:
                            print(f"    - {user}: {user_commit_count[user]} 个提交")
                    else:
                        print(f"  警告: 没有找到匹配的用户。请检查用户名是否正确。")
                        print(f"  您指定的用户: {', '.join(user_names)}")
                        print(f"  实际的提交作者: {', '.join(unique_authors)}")
                        if fuzzy_match:
                            print("  提示: 已启用模糊匹配，但仍未找到匹配。尝试调整用户名以匹配提交者名称。")
                else:
                    print("  没有找到任何提交作者信息")
                        
            except Exception as e:
                print(f"获取分支 {branch_name} 的提交时出错: {e}")
                continue
    
    # Print name mappings if fuzzy matching was used
    if fuzzy_match and name_mappings:
        mapped_authors = [author for author, user in name_mappings.items() if user]
        if mapped_authors:
            print("\n===== 用户名匹配结果 =====")
            for author in mapped_authors:
                print(f"提交作者 '{author}' -> 匹配到用户 '{name_mappings[author]}'")
    
    return stats

def export_to_excel(stats, output_file="gitlab_statistics.xlsx", scale_factor=1):
    """
    Export statistics to Excel
    
    Args:
        stats (dict): Statistics dictionary
        output_file (str): Output Excel file name
        scale_factor (float): Scale factor for statistics
    """
    # Create user summary dataframe
    user_data = []
    for user, user_stats in stats.items():
        # Apply scaling to all numeric values
        total_commits = apply_scale_factor(user_stats["total_commits"], scale_factor)
        total_additions = apply_scale_factor(user_stats["total_additions"], scale_factor)
        total_deletions = apply_scale_factor(user_stats["total_deletions"], scale_factor)
        total_changes = apply_scale_factor(total_additions + total_deletions, scale_factor)
        
        user_data.append({
            "用户": user,
            "总提交次数": total_commits,
            "总增加行数": total_additions,
            "总删除行数": total_deletions,
            "总变更行数": total_changes
        })
    
    user_df = pd.DataFrame(user_data)
    
    # Create repository details dataframe
    repo_data = []
    for user, user_stats in stats.items():
        for repo, repo_stats in user_stats["repos"].items():
            if repo_stats["commits"] > 0:  # Only include repos with commits
                # Apply scaling to all numeric values
                commits = apply_scale_factor(repo_stats["commits"], scale_factor)
                additions = apply_scale_factor(repo_stats["additions"], scale_factor)
                deletions = apply_scale_factor(repo_stats["deletions"], scale_factor)
                changes = apply_scale_factor(additions + deletions, scale_factor)
                
                repo_data.append({
                    "用户": user,
                    "仓库": repo,
                    "提交次数": commits,
                    "增加行数": additions,
                    "删除行数": deletions,
                    "变更行数": changes
                })
    
    repo_df = pd.DataFrame(repo_data)
    
    # Create branch details dataframe
    branch_data = []
    for user, user_stats in stats.items():
        for repo, repo_stats in user_stats["repos"].items():
            for branch, branch_stats in repo_stats["branches"].items():
                if branch_stats["commits"] > 0:  # Only include branches with commits
                    # Apply scaling to all numeric values
                    commits = apply_scale_factor(branch_stats["commits"], scale_factor)
                    additions = apply_scale_factor(branch_stats["additions"], scale_factor)
                    deletions = apply_scale_factor(branch_stats["deletions"], scale_factor)
                    changes = apply_scale_factor(additions + deletions, scale_factor)
                    
                    branch_data.append({
                        "用户": user,
                        "仓库": repo,
                        "分支": branch,
                        "提交次数": commits,
                        "增加行数": additions,
                        "删除行数": deletions,
                        "变更行数": changes
                    })
    
    branch_df = pd.DataFrame(branch_data)
    
    try:
        # Export to Excel
        with pd.ExcelWriter(output_file) as writer:
            user_df.to_excel(writer, sheet_name="用户汇总", index=False)
            repo_df.to_excel(writer, sheet_name="仓库详情", index=False)
            branch_df.to_excel(writer, sheet_name="分支详情", index=False)
        
        if scale_factor != 1:
            print(f"数据已按比例调整 (缩放因子: {scale_factor})")
        print(f"统计数据已导出到 {output_file}")
        return output_file
    except Exception as e:
        print(f"导出到Excel时出错: {e}")
        # Try to save as CSV if Excel export fails
        try:
            user_df.to_csv("用户汇总.csv", index=False, encoding='utf-8-sig')
            repo_df.to_csv("仓库详情.csv", index=False, encoding='utf-8-sig')
            branch_df.to_csv("分支详情.csv", index=False, encoding='utf-8-sig')
            print("由于Excel导出失败，已将数据保存为CSV文件")
            return "CSV files"
        except Exception as csv_e:
            print(f"保存为CSV时出错: {csv_e}")
            return None

def validate_statistics(stats):
    """
    Validate the generated statistics
    
    Args:
        stats (dict): Statistics dictionary
    
    Returns:
        bool: True if valid, False otherwise
    """
    if not stats:
        return False
    
    # Check if any commits were found
    has_commits = False
    for user, user_stats in stats.items():
        if user_stats["total_commits"] > 0:
            has_commits = True
            break
    
    if not has_commits:
        print("\n未找到所指定用户的提交数据。可能的原因:")
        print("1. 日期范围内没有这些用户的提交")
        print("2. 用户名与提交时使用的名称不完全匹配")
        print("3. 所选仓库或分支不包含这些用户的提交")
    
    return has_commits

def main():
    # Get user input
    params = get_user_input()
    
    # Print summary of parameters
    print("\n=== 统计参数 ===")
    print(f"日期范围: {params['start_date']} 至 {params['end_date']}")
    print(f"仓库: {', '.join(params['repo_paths'])}")
    print(f"用户: {', '.join(params['user_names'])}")
    print(f"用户名模糊匹配: {'启用' if params['fuzzy_match'] else '禁用'}")
    print(f"最大分支数: {params['max_branches']}")
    print(f"数据缩放因子: {params['scale_factor']}")
    
    # Get statistics
    stats = get_commit_statistics(
        params['gitlab_url'],
        params['gitlab_token'],
        params['repo_paths'],
        params['user_names'],
        params['start_date'],
        params['end_date'],
        params['fuzzy_match'],
        params['max_branches']
    )
    
    # Validate statistics
    if validate_statistics(stats):
        # Export to Excel
        output_file = export_to_excel(stats, params['output_file'], params['scale_factor'])
        if output_file:
            print(f"\n分析完成! 结果已保存到 {output_file}")
    else:
        print("\n未找到符合条件的提交数据，请检查参数是否正确。")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序已中断")
    except Exception as e:
        print(f"\n程序执行出错: {e}")
