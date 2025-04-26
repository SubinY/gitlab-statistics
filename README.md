# GitLab 代码统计工具

一个用于统计GitLab仓库中代码提交情况的Python工具，可以按用户、仓库和分支统计提交次数和代码行数变更。

## 功能特点

- 支持按日期范围统计代码提交
- 支持统计多个仓库和多个用户
- 支持用户名模糊匹配，解决提交作者名和显示名不匹配的问题
- 自动识别仓库最活跃的分支
- 导出统计结果到Excel文件，包含用户汇总、仓库详情和分支详情三个表格
- 提供交互式命令行界面，易于使用

## 安装说明

### 1. 克隆仓库

```bash
git clone https://github.com/huxiubin/gitlab-statistics.git
cd gitlab-statistics
```

### 2. 安装依赖

使用requirements.txt安装依赖（推荐）:

```bash
pip install -r requirements.txt
```

或者手动安装各个依赖:

```bash
pip install python-gitlab pandas openpyxl
```

### 3. 配置参数

1. 复制配置模板文件创建自己的配置文件：

```bash
cp config.template.py config.py
```

2. 编辑`config.py`文件，填写您的GitLab URL和访问令牌：

```python
# GitLab 配置
GITLAB_URL = "http://your-gitlab-server.com"
GITLAB_TOKEN = "your_access_token_here"

# 其他配置...
```

## 使用方法

1. 运行脚本：

```bash
python gitlab_statistics.py
```

2. 按照提示输入参数，或直接按回车使用配置文件中的默认值
3. 程序会自动连接GitLab，获取仓库信息，分析提交数据，最后生成Excel统计报告

## 配置文件说明

`config.py`文件包含以下配置项：

- `GITLAB_URL`: GitLab服务器URL
- `GITLAB_TOKEN`: GitLab访问令牌
- `DEFAULT_START_DATE`: 默认开始日期，格式为"YYYY-MM-DD"
- `DEFAULT_END_DATE`: 默认结束日期，格式为"YYYY-MM-DD"
- `DEFAULT_REPOSITORIES`: 默认仓库路径，使用逗号分隔
- `DEFAULT_USERS`: 默认用户名列表，使用逗号分隔
- `DEFAULT_FUZZY_MATCH`: 是否默认启用模糊匹配
- `DEFAULT_MAX_BRANCHES`: 每个仓库默认分析的最大分支数
- `DEFAULT_OUTPUT_FILE`: 默认输出的Excel文件名
- `USER_NAME_MAPPINGS`: 用户名映射表，用于匹配不同形式的用户名

## 输出结果说明

生成的Excel文件包含三个表格：

1. **用户汇总**：每个用户的总提交次数、新增/删除/变更行数
2. **仓库详情**：每个用户在每个仓库的提交统计
3. **分支详情**：每个用户在每个仓库的每个分支的提交统计

## 注意事项

- 请确保您的GitLab访问令牌有足够的权限访问所需的仓库
- 为保护您的访问令牌，请勿将包含真实令牌的`config.py`文件提交到公共仓库
- 对于大型仓库或长时间范围的统计，程序运行可能需要较长时间
- 如果您使用的是自托管的GitLab，请确保您的网络能够访问该服务器

## 问题排查

如遇到"未找到仓库"错误，可能的解决方法：

1. 确认仓库路径是否正确，包括组名和项目名
2. 检查GitLab令牌是否有权限访问该仓库
3. 利用程序输出的仓库列表，选择正确的仓库路径

如遇到"未找到用户提交"错误，可能的解决方法：

1. 检查用户名是否与GitLab提交记录中的作者名一致
2. 在`config.py`的`USER_NAME_MAPPINGS`中添加作者名到用户名的映射
3. 确认指定的日期范围内是否有该用户的提交 