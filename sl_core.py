import sys
import json
import argparse
import matlab.engine

# === 智能连接管理器 ===
def connect_to_session(target_name=None):
    """Finds and connects to a shared MATLAB session."""
    sessions = matlab.engine.find_matlab()
    
    # === Case A: 一个共享都没开 (优化显示) ===
    if not sessions:
        # 1. 使用 sys.stderr 输出给人类看（支持换行，带分割线）
        sys.stderr.write("\n" + "="*55 + "\n")
        sys.stderr.write(" [CRITICAL ERROR] No shared MATLAB session found.\n")
        sys.stderr.write(" " + "-"*53 + "\n")
        sys.stderr.write(" ACTION REQUIRED:\n")
        sys.stderr.write(" 1. Go to your MATLAB Command Window.\n")
        sys.stderr.write(" 2. Type and run: matlab.engine.shareEngine\n")
        sys.stderr.write("="*55 + "\n\n")
        
        # 2. 输出给 AI 程序看 (JSON 格式，简洁，不包含长篇大论)
        # 这样 AI 读到 JSON 知道出错了，而你在屏幕上看到了漂亮的提示
        print(json.dumps({"error": "No shared MATLAB session found. User notified via stderr."}))
        
        # 3. 直接退出，不再抛出异常让 main 函数处理
        sys.exit(1)

    # === Case B: 连接逻辑 (保持不变) ===
    target = target_name if target_name else sessions[0]
    
    if target_name and target not in sessions:
        # 如果指定了名字但没找到，同样处理
        sys.stderr.write(f"\n[ERROR] Session '{target}' not found. Available: {sessions}\n")
        print(json.dumps({"error": f"Session '{target}' not found."}))
        sys.exit(1)
        
    if len(sessions) > 1 and not target_name:
        sys.stderr.write(f"[INFO] Multiple sessions found {sessions}. Connecting to '{target}'.\n")
        
    return matlab.engine.connect_matlab(target)

# === 核心功能区 (保持不变或微调) ===
def get_model_structure(eng):
    try:
        model_name = eng.bdroot()
        if not model_name:
            return {"error": "No active model found. Please open a Simulink model."}
            
        blocks = eng.find_system(model_name, 'SearchDepth', 1, 'Type', 'block')
        block_list = []
        for blk in blocks:
            if blk == model_name: continue
            b_type = eng.get_param(blk, 'BlockType')
            item = {'name': blk, 'type': b_type}
            block_list.append(item)

        # 简单的连线获取逻辑 (这里简化展示，用你之前那个复杂的版本也可以)
        lines = eng.find_system(model_name, 'SearchDepth', 1, 'FindAll', True, 'Type', 'line')
        if isinstance(lines, float): lines = [lines]
        if not lines: lines = []
        
        connections = []
        # ... (此处省略连线遍历代码，请保留你之前那个好用的版本) ...
        # 为节省篇幅，这里假设你已经把之前的 connection 代码放进来了
        
        return {"model": model_name, "blocks": block_list, "connections": connections}
    except Exception as e:
        return {"error": str(e)}

def highlight_block(eng, block_path):
    try:
        eng.hilite_system(block_path, 'find', nargout=0)
        return {"status": "success", "highlighted": block_path}
    except Exception as e:
        return {"error": str(e)}

# === CLI 入口 ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulink AI Bridge Core")
    parser.add_argument('action', choices=['scan', 'highlight'], help="Action to perform")
    parser.add_argument('--target', help="Target for highlight")
    parser.add_argument('--session', help="Specific MATLAB session name to connect to")
    
    args = parser.parse_args()
    
    try:
        # 使用智能连接
        eng = connect_to_session(args.session)
        
        output = {}
        if args.action == 'scan':
            output = get_model_structure(eng)
        elif args.action == 'highlight':
            if args.target:
                output = highlight_block(eng, args.target)
            else:
                output = {"error": "Missing --target"}
        
        print(json.dumps(output, indent=2))
        
    except RuntimeError as e:
        # 捕获我们自定义的连接错误，直接打印给 AI 看
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"Unexpected error: {str(e)}"}))
        sys.exit(1)