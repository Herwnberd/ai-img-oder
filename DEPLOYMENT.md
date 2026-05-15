# 帽子云部署指南

## 重要安全提醒
⚠️ 请勿将密钥硬编码在代码中！使用环境变量管理敏感信息。

## 登录帽子云
1. 访问帽子云控制台: https://www.maozi.io/
2. 账号: 18826295534
3. 密码: hewenbin9013

## 部署步骤

### 1. 创建应用
- 登录后进入控制台
- 找到"应用部署"或"容器服务"
- 创建新应用，选择"Python Flask"模板

### 2. 上传代码
- 将以下文件打包成ZIP:
  - app.py
  - start.py
  - gunicorn.conf.py
  - requirements.txt
  - templates/ (整个目录)
  - uploads/ (整个目录，可选)
  - .env.example (可选，作为参考)

### 3. 配置环境变量
在帽子云的环境变量设置中添加以下配置：

| 变量名 | 值 |
|--------|-----|
| API_URL | https://147ai.com |
| API_KEY | sk-SwMOol9j0ZtVAAcWLIxX7fpzekkKn1Poq8Cu1b3kyYorwVDo |
| MODEL | gpt-image-2-client |
| TOS_REGION | cn-guangzhou |
| TOS_ENDPOINT | tos-cn-guangzhou.volces.com |
| TOS_BUCKET | traetos01 |
| TOS_ACCESS_KEY | AKLTOGI5ZmY4MzI4OGUzNDA1MTk4YjA0ODBmMTEyNDZjZDM |
| TOS_SECRET_KEY | WldabVpEY3lOVE01T0RCaU5HTmhNamhqTURObVltUTJZekJsTVRoaE9EUQ== |

### 4. 配置启动命令
```bash
gunicorn -c gunicorn.conf.py app:app
```

### 5. 配置域名
- 进入域名管理
- 添加域名: imgoder-izfqk01ae.maozi.io
- 配置SSL证书(自动生成)

### 6. 启动应用
- 点击"启动"按钮
- 等待部署完成

## 本地开发测试
创建 .env 文件并设置环境变量：
```bash
cp .env.example .env
# 编辑 .env 文件填写实际值
python app.py
```

## 项目结构
```
image_gen_app/
├── app.py              # Flask主程序
├── start.py            # Waitress启动脚本
├── gunicorn.conf.py    # Gunicorn配置
├── requirements.txt    # 依赖清单
├── .env.example        # 环境变量示例
├── templates/          # HTML模板
│   └── index.html      # 前端页面
└── uploads/            # 上传文件存储
```

## 测试访问
部署成功后访问: https://imgoder-izfqk01ae.maozi.io/

## 故障排除
- 检查日志文件: access.log, error.log
- 确保环境变量已正确设置
- 确保端口5000已开放
- 检查依赖是否安装成功

## 安全最佳实践
1. 🔒 使用环境变量存储敏感信息
2. 🔒 不在代码中硬编码密钥
3. 🔒 定期轮换API密钥
4. 🔒 使用HTTPS协议
5. 🔒 限制Bucket访问权限