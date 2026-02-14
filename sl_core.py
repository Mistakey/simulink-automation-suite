import sys
import json
import argparse
import matlab.engine

# === 全局连接保持逻辑 ===
# 注意：MATLAB Engine 启动较慢，CLI 每次运行都会重连。
# 生产环境建议用 Server 模式，但为了简单，这里演示 Shared Session 连接。

def connect_matlab(session_name=None):
    """连接到共享的 MATLAB Session"""
    try:
        # 查找现有共享会话
        sessions = matlab.engine.find_matlab()
        if not sessions:
            return None, "Error: No shared MATLAB sessions found. Run 'matlab.engine.shareEngine' in MATLAB."
        
        # 如果指定了名称就连指定的，否则连第一个
        target = session_name if session_name else sessions[0]
        eng = matlab.engine.connect_matlab(target)
        return eng, None
    except Exception as e:
        return None, str(e)

def get_model_structure(eng):
    """获取当前模型的顶层结构（包含模块 + 连接关系）"""
    try:
        model_name = eng.bdroot() # 获取当前活动模型
        
        # === 1. 获取模块清单 ===
        blocks = eng.find_system(model_name, 'SearchDepth', 1, 'Type', 'block')
        block_list = []
        for blk in blocks:
            if blk == model_name: continue
            b_type = eng.get_param(blk, 'BlockType')
            item = {'name': blk, 'type': b_type}
            
            # 提取关键参数 (可以根据需要扩展)
            if b_type == 'Constant':
                item['value'] = eng.get_param(blk, 'Value')
            elif b_type == 'Gain':
                item['gain'] = eng.get_param(blk, 'Gain')
            elif b_type == 'SubSystem':
                # 标记一下子系统，方便后续 AI 决定是否要深入
                item['is_subsystem'] = True
                
            block_list.append(item)

        # === 2. 获取连线关系 (核心升级) ===
        # find_system 查找当前层级所有的线
        lines = eng.find_system(model_name, 'SearchDepth', 1, 'FindAll', True, 'Type', 'line')
        
        # 如果 lines 是单个 float (只有一根线的情况)，转为列表
        # 注意：matlab engine 返回的 lines 可能是 float 或 list
        if isinstance(lines, float): lines = [lines]
        if not lines: lines = [] # 空列表处理

        connection_list = []
        for line in lines:
            try:
                # 获取线的源头 (Handle)
                src_port = eng.get_param(line, 'SrcPortHandle')
                
                # 如果线悬空 (没有源头)，跳过
                if isinstance(src_port, float) and src_port == -1.0: continue

                # 获取源模块名
                src_block_handle = eng.get_param(src_port, 'Parent')
                src_block_name = eng.get_param(src_block_handle, 'Name')

                # 获取线的所有终点 (一根线可能分叉连到多个模块)
                dst_ports = eng.get_param(line, 'DstPortHandle')
                
                # 统一转为列表处理
                if isinstance(dst_ports, float): dst_ports = [dst_ports]
                
                for dst_port in dst_ports:
                    dst_block_handle = eng.get_param(dst_port, 'Parent')
                    dst_block_name = eng.get_param(dst_block_handle, 'Name')
                    
                    # 记录一条连接: Source -> Destination
                    connection_list.append({
                        "src": src_block_name,
                        "dst": dst_block_name
                    })
            except Exception as e:
                # 忽略某些特殊线的报错（如注解线）
                continue
            
        return {
            "model": model_name, 
            "blocks": block_list,
            "connections": connection_list  # 新增的连线字段
        }
    except Exception as e:
        return {"error": str(e)}

def highlight_block(eng, block_path):
    """在 Simulink 中高亮指定模块"""
    try:
        eng.hilite_system(block_path, 'find', nargout=0)
        return {"status": "success", "highlighted": block_path}
    except Exception as e:
        return {"error": str(e)}

# === CLI 入口 ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulink AI Bridge Tool")
    parser.add_argument('action', choices=['scan', 'highlight', 'get_param'], help="Action to perform")
    parser.add_argument('--target', help="Target block path or parameter name")
    
    args = parser.parse_args()
    
    eng, err = connect_matlab()
    if err:
        print(json.dumps({"error": err}))
        sys.exit(1)

    output = {}
    if args.action == 'scan':
        output = get_model_structure(eng)
    elif args.action == 'highlight':
        if args.target:
            output = highlight_block(eng, args.target)
        else:
            output = {"error": "Missing --target for highlight"}
            
    # 输出 JSON 给 Claude 读取
    print(json.dumps(output, indent=2))