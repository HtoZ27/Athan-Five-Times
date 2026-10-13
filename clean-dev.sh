#!/bin/bash
# =============================================================================
# clean-dev.sh - أداة تنظيف بيئة التطوير
# =============================================================================
# تقوم بتنظيف المخلفات، تحرير المنافذ، مسح الذاكرة المؤقتة
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}      تنظيف بيئة التطوير (clean-dev)        ${NC}"
echo -e "${CYAN}============================================${NC}"

# 1. قتل عمليات Python القديمة (باستثناء الجلسة الحالية)
echo -e "\n${YELLOW}[1] قتل عمليات Python المعلقة...${NC}"
CURRENT_PID=$$
PYTHON_PIDS=$(pgrep -f "python3.*backend.main" 2>/dev/null || true)
for pid in $PYTHON_PIDS; do
    if [ "$pid" != "$CURRENT_PID" ] && [ "$pid" != "$(ps -o ppid= -p $CURRENT_PID 2>/dev/null | tr -d ' ')" ]; then
        kill -15 "$pid" 2>/dev/null && echo -e "  ${GREEN}قتل PID $pid${NC}" || echo -e "  ${RED}فشل قتل PID $pid${NC}"
    fi
done

# 2. تحرير المنافذ
echo -e "\n${YELLOW}[2] تحرير المنافذ...${NC}"
for port in 3000 5173 8080 4173; do
    pid=$(lsof -ti :$port 2>/dev/null || true)
    if [ -n "$pid" ]; then
        kill -15 $pid 2>/dev/null && echo -e "  ${GREEN}المنفذ $port -> تم التحرير${NC}" || echo -e "  ${RED}المنفذ $port -> فشل التحرير${NC}"
    else
        echo -e "  ${GREEN}المنفذ $port -> حر${NC}"
    fi
done

# 3. تنظيف __pycache__
echo -e "\n${YELLOW}[3] تنظيف __pycache__ و .pyc...${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
find "$SCRIPT_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null && echo -e "  ${GREEN}__pycache__ -> تم الحذف${NC}"
find "$SCRIPT_DIR" -name "*.pyc" -delete 2>/dev/null && echo -e "  ${GREEN}*.pyc -> تم الحذف${NC}"
find "$SCRIPT_DIR" -name "*.pyo" -delete 2>/dev/null && echo -e "  ${GREEN}*.pyo -> تم الحذف${NC}"

# 4. تنظيف .pytest_cache
if [ -d "$SCRIPT_DIR/.pytest_cache" ]; then
    rm -rf "$SCRIPT_DIR/.pytest_cache" 2>/dev/null && echo -e "  ${GREEN}.pytest_cache -> تم الحذف${NC}"
fi

# 5. تنظيف ملفات الـ Build
echo -e "\n${YELLOW}[4] تنظيف ملفات البناء...${NC}"
for d in "$SCRIPT_DIR"/dist "$SCRIPT_DIR"/build "$SCRIPT_DIR"/AppDir/usr; do
    if [ -d "$d" ]; then
        rm -rf "$d" 2>/dev/null && echo -e "  ${GREEN}$d -> تم الحذف${NC}" || echo -e "  ${RED}$d -> فشل الحذف${NC}"
    fi
done

# 6. تنظيف pip cache
echo -e "\n${YELLOW}[5] تنظيف pip cache...${NC}"
pip cache purge 2>/dev/null && echo -e "  ${GREEN}pip cache -> تم التنظيف${NC}" || echo -e "  ${RED}pip cache -> فشل${NC}"

# 7. تنظيف npm cache لو موجود
if command -v npm &>/dev/null && [ -d "$SCRIPT_DIR/node_modules" ]; then
    echo -e "\n${YELLOW}[6] تنظيف npm cache...${NC}"
    npm cache clean --force 2>/dev/null && echo -e "  ${GREEN}npm cache -> تم التنظيف${NC}" || echo -e "  ${RED}npm cache -> فشل${NC}"
fi

# 8. عرض الذاكرة المحررة
echo -e "\n${YELLOW}[7] حالة الذاكرة بعد التنظيف:${NC}"
if command -v free &>/dev/null; then
    free -h | head -2
fi

# 9. التقرير النهائي
echo -e "\n${CYAN}============================================${NC}"
echo -e "${GREEN}          تم التنظيف بنجاح ✅               ${NC}"
echo -e "${CYAN}============================================${NC}"
echo -e "  ${GREEN}المنافذ المحررة: 3000, 5173, 8080, 4173${NC}"
echo -e "  ${GREEN}ملفات cache: تم الحذف${NC}"
echo -e "  ${GREEN}عمليات Python: تم الإنهاء${NC}"
echo -e "${CYAN}============================================${NC}\n"
