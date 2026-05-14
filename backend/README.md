# 家庭资产管家 - 后端服务

## 快速启动

### 1. 安装依赖
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
```

### 2. 数据库
需要 PostgreSQL 数据库：
```bash
# 创建数据库
createdb family_asset

# 复制环境变量
cp .env.example .env
# 编辑 .env 填入数据库连接信息
```

### 3. 启动服务
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API 文档: http://localhost:8000/docs

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/auth/sms/send | 发送验证码 |
| POST | /api/v1/auth/login | 登录 |
| GET | /api/v1/auth/me | 当前用户信息 |
| POST | /api/v1/auth/family/create | 创建家庭 |
| POST | /api/v1/auth/family/join | 加入家庭 |
| GET | /api/v1/family/detail | 家庭详情 |
| GET | /api/v1/family/members | 成员列表 |
| GET | /api/v1/assets/summary | 资产汇总（首页） |
| GET | /api/v1/assets/list | 资产列表（详情页） |
| POST | /api/v1/assets | 手动录入资产 |
| PUT | /api/v1/assets/{id} | 更新资产 |
| DELETE | /api/v1/assets/{id} | 删除资产 |
| POST | /api/v1/assets/ocr/upload | 截图 OCR 识别 |
| POST | /api/v1/assets/ocr/confirm | 确认识别结果 |
| GET | /api/v1/exchange/rates | 汇率查询 |

## 项目结构

```
backend/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── api/                 # API 路由
│   │   ├── auth.py          # 认证（登录/注册/家庭）
│   │   ├── family.py        # 家庭管理
│   │   ├── assets.py        # 资产 CRUD + OCR
│   │   └── exchange.py      # 汇率
│   ├── models/
│   │   ├── models.py        # SQLAlchemy 数据模型
│   │   └── schemas.py       # Pydantic 请求/响应模型
│   ├── services/
│   │   ├── ocr_service.py   # OCR 识别服务
│   │   └── exchange_service.py  # 汇率服务
│   └── core/
│       ├── config.py        # 配置管理
│       ├── database.py      # 数据库连接
│       └── auth.py          # JWT 认证
├── requirements.txt
└── .env.example
```
