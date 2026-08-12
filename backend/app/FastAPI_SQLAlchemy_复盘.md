# FastAPI + SQLAlchemy 复盘

## 1. 项目分层

这个项目主要分成几层：

```text
routers：接收 HTTP 请求，调用 service，把业务异常转成 HTTPException
schemas：定义请求体和响应体的数据结构，并做基础校验
services：处理业务逻辑，查数据库，改数据库，提交事务
models：定义数据库表结构，也就是 ORM 模型
exceptions：定义业务异常类型
database：创建数据库连接和 Session
migrations：保存 Alembic 数据库迁移文件
```

一句话：

```text
routes 接请求，schemas 管数据，services 做业务，models 管表结构。
```

## 2. POST /tasks 创建任务流程

创建任务时，请求大概是：

```http
POST /tasks
```

```json
{
  "title": "学习 FastAPI",
  "priority": 3
}
```

执行流程：

```text
1. routers/tasks.py 接到请求
2. TaskCreate 校验请求体
3. create_task_service 做业务处理
4. TaskORM 创建数据库对象
5. db.add() 加入 Session
6. db.commit() 保存到数据库
7. db.refresh() 读回最新对象
8. TaskResponse 控制返回字段
```

关键理解：

```text
TaskCreate = 创建时允许前端传什么
TaskORM = 数据库怎么存
TaskResponse = 返回给前端看什么
```

## 3. PATCH /tasks/{id} 修改任务流程

修改任务时，请求大概是：

```http
PATCH /tasks/3
```

```json
{
  "done": true
}
```

执行流程：

```text
1. task_id 来自路径参数，表示改哪条任务
2. TaskUpdate 校验请求体，表示改什么
3. model_dump(exclude_unset=True) 取出用户真正传了哪些字段
4. get_task_service 先查任务是否存在
5. setattr 动态修改 ORM 对象属性
6. updated_at 自动更新时间
7. db.commit() 保存
8. db.refresh() 返回最新对象
```

核心代码思路：

```python
update_data = task_update.model_dump(exclude_unset=True)

for field_name, value in update_data.items():
    setattr(task, field_name, value)
```

记法：

```text
没传 = 不修改
传了 null = 明确改成 None
传了合法值 = 修改成这个值
```

## 4. Create / Update / Response 的区别

```text
TaskCreate：创建时能传什么
TaskUpdate：修改时能传什么
TaskResponse：返回时能看到什么
```

例子：

```text
id：不让前端传，但要返回
created_at：通常后端生成，不让前端传，但可以返回
updated_at：后端修改时自动更新，不让前端传，但可以返回
title：创建时必填，修改时可选但不能为空
due_date：可以传 null，用来清空截止日期
```

重要规则：

```text
ORM 里能存，不代表接口输入里能传。
Response 里能看到，不代表 Create/Update 里能提交。
```

## 5. Path / Query / Body / Header

```text
Path：路径参数，表示哪个资源
Query：查询参数，表示怎么筛选
Body：请求体，表示提交什么数据
Header：请求头，表示附加信息，比如认证
```

例子：

```http
PATCH /tasks/3
```

```text
3 是 Path，表示任务 id
```

```http
GET /tasks?done=false&keyword=SQL
```

```text
done 和 keyword 是 Query，表示过滤条件
```

```json
{
  "title": "新标题"
}
```

```text
这是 Body，表示要提交的数据
```

```http
Authorization: Bearer user-1
```

```text
这是 Header，表示当前登录身份
```

## 6. Depends 依赖注入

`Depends` 的意思是：

```text
FastAPI 先执行依赖函数，再把结果传给接口参数。
```

常见例子：

```python
db: Session = Depends(get_db)
```

表示：

```text
先创建数据库 Session，再传给 db 参数。
```

```python
current_user: UserORM = Depends(get_dev_current_user)
```

表示：

```text
先根据 token 查当前用户，再传给 current_user。
```

记法：

```text
get_db 准备数据库工具
get_dev_current_user 准备当前身份
```

## 7. 认证和权限

```text
401 = 没认证成功，比如没 token、token 错
403 = 已经知道你是谁，但你没权限
```

`/tasks/me` 的当前用户来自：

```text
Authorization 请求头里的 token
```

不是来自请求体里的 `user_id`。

记法：

```text
/me = 后端根据 token 判断“我是谁”
user_id = 客户端显式指定用户
```

## 8. 业务异常和 HTTPException

项目内部用业务异常：

```python
TaskNotFoundError
DuplicateTitleError
EmptyUpdateError
UserNotFoundError
```

router 再把它们转成 HTTP 响应：

```python
except TaskNotFoundError:
    raise HTTPException(status_code=404, detail="task not found")
```

分层规则：

```text
service 发现业务问题
exceptions 表达问题名字
router 转成 HTTP 状态码
```

状态码记法：

```text
200：成功
400：请求能看懂，但业务不允许
401：认证失败
403：认证成功但没权限
404：资源不存在
422：参数格式或类型校验失败
```

## 9. 数据库事务

常见操作：

```text
db.add()：把对象加入 Session
db.flush()：把 SQL 先发给数据库，常用于提前拿 id
db.commit()：真正提交事务
db.rollback()：撤销失败事务，并让 Session 恢复可用
db.refresh()：重新从数据库读取最新对象
```

典型流程：

```python
db.add(user_orm)
db.flush()

db.add(task_orm)
db.commit()
db.refresh(user_orm)
```

记法：

```text
flush = 提前拿 id
commit = 真保存
rollback = 撤销这次事务
refresh = 读回最新状态
```

## 10. 数据库约束和业务校验

三层防线：

```text
schema：防脏输入
service：防业务错误
database：最终兜底
```

例子：

```text
title 不能为空：schema 校验
title 是否重复：service 可以提前判断
title 绝对不能重复：database UNIQUE 兜底
user_id 是否存在：service 提前检查
user_id 必须指向真实用户：database FOREIGN KEY 兜底
```

记法：

```text
service 检查是体验，数据库约束是底线。
```

## 11. 分页和排序

分页字段：

```text
items：当前页数据
total：符合条件的总数量
count：当前页返回几条
limit：本次最多取几条
offset：本次跳过几条
has_more：后面是否还有数据
next_offset：下一次从哪里开始取
```

`count` 和 `total` 的区别：

```text
count = 当前页数量
total = 全部符合条件的数量
```

分页要有稳定排序：

```python
statement = statement.order_by(TaskORM.id.asc())
```

如果按 `priority` 排序，最好加 `id` 兜底：

```python
statement = statement.order_by(TaskORM.priority.asc(), TaskORM.id.asc())
```

记法：

```text
先排序，再分页。
主排序字段可能重复时，用 id 兜底。
```

## 12. 动态查询

动态查询就是：

```text
用户传什么条件，就加什么 where。
```

例子：

```python
statement = select(TaskORM)

if done is not None:
    statement = statement.where(TaskORM.done == done)

if keyword is not None:
    statement = statement.where(TaskORM.title.contains(keyword))
```

`contains` 的意思：

```text
标题里包含某个关键词
```

大概相当于 SQL：

```sql
title LIKE '%SQL%'
```

注意：

```text
statement 和 count_statement 要加同样的过滤条件。
```

否则列表数据和 total 会对不上。

## 13. selectinload

`selectinload` 用来预加载关联数据。

比如：

```python
select(UserORM).options(selectinload(UserORM.tasks))
```

意思是：

```text
查用户时，把这个用户的任务列表也提前查出来。
```

适合：

```text
详情接口要返回关联数据
一对多关系，比如 user.tasks
```

局限：

```text
如果根本不用关联数据，就不要提前查。
```

记法：

```text
用得到关联数据 -> selectinload
用不到 -> 不要乱加
```

## 14. Alembic 迁移

当 ORM 表结构变化时，数据库也要跟着变。

比如新增字段：

```text
TaskORM 增加 updated_at
schemas 增加响应字段
service 修改时更新时间
Alembic 增加迁移文件
执行 alembic upgrade head
```

记法：

```text
改 ORM 只是改 Python 代码；
迁移才是改真实数据库结构。
```

SQLite 注意点：

```text
SQLite 不能直接 ADD COLUMN 一个非空且默认 CURRENT_TIMESTAMP 的字段。
```

所以迁移里常用步骤：

```text
1. 先加 nullable=True 的列
2. 给旧数据填值
3. 再改成 nullable=False
```

## 15. 最后一张总图

```text
HTTP 请求
  ↓
router 接请求
  ↓
schema 校验输入
  ↓
service 做业务
  ↓
model / ORM 操作数据库
  ↓
commit / rollback / refresh
  ↓
response_model 控制输出
  ↓
HTTP 响应
```

这是 FastAPI + SQLAlchemy 项目的主线。
