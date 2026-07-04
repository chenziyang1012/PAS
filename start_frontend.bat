@echo off
echo === 启动产品审核系统前端 ===
cd /d "%~dp0frontend"
if not exist node_modules (
    echo 安装依赖...
    npm install
)
echo 启动前端开发服务 http://localhost:5173
npm run dev
