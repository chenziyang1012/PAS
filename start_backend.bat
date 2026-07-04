@echo off
echo === 启动产品审核系统后端 ===
cd /d "%~dp0backend"
if not exist venv (
    echo 创建虚拟环境...
    python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt -q
echo 初始化数据库和管理员账号...
python init_data.py
echo 启动后端服务 http://localhost:8000
uvicorn main:app --reload --host 0.0.0.0 --port 8000
