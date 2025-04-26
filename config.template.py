# GitLab 配置
# 请填写您的GitLab URL和访问令牌
GITLAB_URL = "http://your-gitlab-server.com"
GITLAB_TOKEN = "your_access_token_here"

# 默认参数配置
# 日期范围
DEFAULT_START_DATE = "2025-01-01"
DEFAULT_END_DATE = "2025-04-26"

# 仓库路径，使用逗号分隔的字符串
DEFAULT_REPOSITORIES = "group/project1,group/project2"

# 用户名，使用逗号分隔的字符串
DEFAULT_USERS = "user1,user2,user3"

# 是否默认启用模糊匹配
DEFAULT_FUZZY_MATCH = True

# 默认每个仓库分析的最大分支数
DEFAULT_MAX_BRANCHES = 1

# 默认输出的Excel文件名
DEFAULT_OUTPUT_FILE = "gitlab_statistics.xlsx"

# 用户名映射表，用于匹配提交作者名与用户名（可以不填）
# 格式: "提交作者名": "映射的用户名"
USER_NAME_MAPPINGS = {
    "author1": "user1",
    "author2": "user2",
    # 可以添加更多映射关系
} 