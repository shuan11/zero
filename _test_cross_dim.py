"""测试交叉维度自学注入"""
import sys, os
sys.path.insert(0, "/mnt/c/Users/h/Desktop/零/真元集群")
os.chdir("/mnt/c/Users/h/Desktop/零/真元集群")

from 自我改进 import _detect_cross_dim_gap, _apply_cross_dim_learn

# 选一个器官测试
test_file = "organs/time_gradient_organ.py"
print(f"检测 {test_file}: {_detect_cross_dim_gap(test_file)}")

# 如果检测通过，应用注入
if _detect_cross_dim_gap(test_file):
    r = _apply_cross_dim_learn(test_file, {})
    print(f"注入结果: {r}")
    if r.get("success"):
        # 检查是否注入了CROSS_DIM_AWARENESS
        content = open(test_file).read()
        if "CROSS_DIM_AWARENESS" in content:
            print("✅ CROSS_DIM_AWARENESS 注入成功!")
            # 提取显示
            for line in content.split('\n'):
                if 'CROSS_DIM_AWARENESS' in line or 'cross_dim_report' in line or '弱交叉' in line:
                    print(f"  {line.strip()}")
        # 回滚修改
        import subprocess
        subprocess.run(["git", "checkout", "--", test_file], capture_output=True)
        print("已回滚测试修改")
    else:
        print(f"注入失败: {r.get('error')}")
else:
    print("未检测到交叉维度缺口")
