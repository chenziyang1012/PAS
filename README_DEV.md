产品审核系统 MVP 开发文档
1. 项目目标

开发一个内部使用的 Web 管理系统，用于支持以下最小流程：

管理员创建和管理用户
用户分为不同角色：管理员、选品员、审核员
选品员手动上传产品
选品员将产品提交给审核员审核
审核员审核产品，结果为通过或驳回
选品员可查看审核结果，若被驳回可修改后重新提交

本期只开发两个核心模块：

用户与权限模块
产品上传 + 审核模块

不开发以下内容：

AI 风险审核
自动抓取公司浏览器系统内容
报价、询盘、箱规
报表统计
消息通知
自定义 RBAC 权限配置页
2. 推荐技术栈
前端
Vue 3
Vite
TypeScript
Element Plus
Vue Router
Pinia
Axios
后端
Python 3.11+
FastAPI
SQLAlchemy
Pydantic
Alembic
JWT 认证
数据库
MySQL 8.x
文件上传
MVP 阶段先使用本地文件存储
数据库存储图片访问路径
3. 角色定义

系统包含 3 个固定角色：

3.1 admin

管理员，拥有全部权限。

3.2 selector

选品员，负责创建和提交产品。

3.3 reviewer

审核员，负责审核产品。

4. 角色权限说明
4.1 管理员 admin

可以：

登录系统
查看当前用户信息
管理用户
创建用户
编辑用户
启用/禁用用户
重置用户密码
查看全部产品
查看全部产品详情
查看全部审核记录
审核产品
必要时修改产品状态
4.2 选品员 selector

可以：

登录系统
查看当前用户信息
创建产品
编辑自己创建的草稿产品
编辑自己创建的驳回产品
删除自己创建的草稿产品
查看自己创建的产品列表
查看自己创建的产品详情
提交自己创建的产品审核

不可以：

审核产品
查看他人产品
编辑待审核产品
编辑已通过产品
4.3 审核员 reviewer

可以：

登录系统
查看当前用户信息
查看待审核产品列表
查看产品详情
审核通过产品
审核驳回产品
查看审核记录

不可以：

创建产品
编辑产品内容
删除产品
管理用户
5. 核心业务流程
5.1 产品提交流程
text
复制代码
收起
选品员创建产品
-> 保存为草稿
-> 提交审核
-> 状态改为待审核
-> 审核员查看待审核产品
-> 审核员审核
   -> 通过：状态改为审核通过
   -> 驳回：状态改为审核驳回，并填写驳回原因
-> 选品员查看结果
-> 若被驳回，选品员可修改并再次提交
复制
6. 产品状态定义

产品状态字段使用以下固定枚举值：

draft：草稿
pending_review：待审核
approved：审核通过
rejected：审核驳回

状态流转规则：

新建产品后默认状态为 draft
draft 可提交为 pending_review
rejected 可重新编辑并再次提交为 pending_review
pending_review 可被审核为：
approved
rejected
approved 不可再编辑
pending_review 不可编辑
draft 可删除
rejected 暂不允许删除（可按需调整）
approved 不可删除
pending_review 不可删除
7. 页面需求
7.1 登录页

功能：

用户名登录
密码登录
登录成功后返回 JWT token
前端保存 token
跳转到工作台或产品页
7.2 工作台首页

简单即可，展示：

当前用户名称
当前角色
快捷入口：
产品列表
待审核列表
用户管理（仅管理员）
7.3 用户管理页（管理员）

功能：

用户列表
新增用户
编辑用户
启用/禁用用户
重置密码

列表字段建议：

用户ID
用户名
姓名
角色
状态
创建时间

表单字段：

用户名
密码（编辑时可不改）
姓名
角色
状态
7.4 产品列表页
选品员视角

只能看到自己创建的产品。

功能：

查看列表
按状态筛选
按产品名称搜索
新建产品
编辑草稿/驳回产品
删除草稿产品
提交审核
查看详情

列表字段建议：

产品ID
产品名称
类目
状态
创建时间
提交时间
操作按钮
管理员视角

可查看全部产品。

7.5 产品新建页 / 编辑页

字段：

产品名称（必填）
产品链接（可选）
产品类目（可选）
产品描述（可选）
产品图片（至少 1 张，必填）

按钮：

保存草稿
提交审核

规则：

保存草稿时状态为 draft
提交审核时需要校验必填字段
若没有图片则不允许提交审核
7.6 产品详情页

展示：

基础信息
图片列表
状态
创建人
提交时间
最近审核结果
驳回原因（如有）
7.7 待审核列表页（审核员）

功能：

查看所有待审核产品
按产品名筛选
查看详情
审核通过
审核驳回

列表字段建议：

产品ID
产品名称
类目
创建人
提交时间
操作
7.8 审核详情页

展示：

产品全部基础信息
产品图片
创建人
创建时间
提交时间

操作：

审核通过
审核驳回

驳回要求：

必须填写驳回原因
8. 后端接口需求

接口统一前缀：

text
复制代码
收起
/api
复制

返回格式建议统一：

json
复制代码
收起
{
  "code": 0,
  "message": "ok",
  "data": {}
}
复制

出错时：

json
复制代码
收起
{
  "code": 4001,
  "message": "error message",
  "data": null
}
复制
8.1 认证接口
POST /api/auth/login

请求：

json
复制代码
收起
{
  "username": "admin",
  "password": "123456"
}
复制

响应：

json
复制代码
收起
{
  "code": 0,
  "message": "ok",
  "data": {
    "token": "jwt_token",
    "user": {
      "id": 1,
      "username": "admin",
      "real_name": "管理员",
      "role": "admin"
    }
  }
}
复制
GET /api/auth/me

获取当前登录用户信息。

POST /api/auth/logout

MVP 可只做前端清 token，后端可保留空实现。

8.2 用户管理接口
GET /api/users

管理员查看用户列表。

支持查询参数：

page
page_size
username
role
status
POST /api/users

管理员新增用户。

请求体：

json
复制代码
收起
{
  "username": "selector01",
  "password": "123456",
  "real_name": "张三",
  "role": "selector",
  "status": "enabled"
}
复制
PUT /api/users/{id}

管理员编辑用户。

PATCH /api/users/{id}/status

修改用户启用/禁用状态。

请求体：

json
复制代码
收起
{
  "status": "disabled"
}
复制
POST /api/users/{id}/reset-password

重置密码。

请求体：

json
复制代码
收起
{
  "new_password": "123456"
}
复制
8.3 产品接口
GET /api/products

获取产品列表。

权限规则：

selector：只能看到自己创建的产品
reviewer：默认不使用此接口查看待审核，可选允许查看部分
admin：可查看全部

支持查询参数：

page
page_size
keyword
status
POST /api/products

创建产品。

请求格式建议使用 multipart/form-data 或先上传图片后提交 JSON。

若使用 JSON，可设计为：

json
复制代码
收起
{
  "product_name": "产品A",
  "product_link": "https://example.com/1",
  "category": "家居",
  "description": "描述内容",
  "images": [
    "/uploads/xxx1.jpg",
    "/uploads/xxx2.jpg"
  ],
  "action": "draft"
}
复制

说明：

action = draft 表示保存草稿
action = submit 表示直接提交审核

如果 action = submit，则创建后状态直接为 pending_review
如果 action = draft，则状态为 draft

GET /api/products/{id}

获取产品详情。

权限规则：

selector 只能查看自己产品
reviewer 可查看待审核/已审核产品
admin 可查看所有产品
PUT /api/products/{id}

编辑产品。

权限规则：

仅创建人可编辑
且状态必须是 draft 或 rejected

请求体：

json
复制代码
收起
{
  "product_name": "产品A-修改",
  "product_link": "https://example.com/1",
  "category": "家居",
  "description": "新的描述",
  "images": [
    "/uploads/xxx1.jpg"
  ]
}
复制
DELETE /api/products/{id}

删除产品。

权限规则：

仅创建人可删除
且仅允许删除 draft
POST /api/products/{id}/submit-review

提交审核。

权限规则：

仅创建人可提交
且状态必须为 draft 或 rejected

提交前校验：

产品名称必填
至少一张图片

提交后：

状态改为 pending_review
记录提交时间
8.4 审核接口
GET /api/reviews/pending

获取待审核产品列表。

权限：

reviewer
admin

支持查询参数：

page
page_size
keyword
GET /api/reviews/{product_id}

获取审核详情页所需信息。

POST /api/reviews/{product_id}/approve

审核通过。

权限：

reviewer
admin

规则：

产品当前状态必须为 pending_review

提交后：

状态改为 approved
写入审核记录

请求体可为空：

json
复制代码
收起
{}
复制
POST /api/reviews/{product_id}/reject

审核驳回。

权限：

reviewer
admin

规则：

产品当前状态必须为 pending_review
驳回原因必填

请求体：

json
复制代码
收起
{
  "reason": "图片不清晰，类目信息不完整"
}
复制

提交后：

状态改为 rejected
写入审核记录
8.5 文件上传接口
POST /api/upload/image

上传单张或多张图片。

权限：

已登录用户

返回：

json
复制代码
收起
{
  "code": 0,
  "message": "ok",
  "data": {
    "url": "/uploads/2026/06/abc.jpg"
  }
}
复制

MVP 阶段：

文件保存在本地目录
数据库存路径
后端提供静态资源访问
9. 数据库设计
9.1 users 表

字段：

id bigint primary key auto_increment
username varchar(50) unique not null
password_hash varchar(255) not null
real_name varchar(50) not null
role varchar(20) not null
status varchar(20) not null default 'enabled'
created_at datetime not null
updated_at datetime not null

约束：

role 仅允许：admin, selector, reviewer
status 仅允许：enabled, disabled
9.2 products 表

字段：

id bigint primary key auto_increment
product_name varchar(255) not null
product_link varchar(500) null
category varchar(100) null
description text null
status varchar(30) not null default 'draft'
creator_id bigint not null
submit_time datetime null
created_at datetime not null
updated_at datetime not null

外键：

creator_id -> users.id

约束：

status 仅允许