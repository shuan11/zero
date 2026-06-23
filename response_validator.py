"""
response_validator.py — API响应验证层
过滤API输出的偏移内容，确保格式符合预期
"""

import re
import json

def validate_response(response_text: str, expected_format: str = "any") -> dict:
    """
    验证API响应是否符合预期格式
    
    Args:
        response_text: API返回的文本
        expected_format: 期望格式 - "json", "code", "python_code", "single_line", "any"
    
    Returns:
        {"valid": bool, "cleaned": str, "reason": str, "retry_penalty": str}
    """
    if not response_text or len(response_text.strip()) < 5:
        return {"valid": False, "cleaned": "", "reason": "响应为空或过短", "retry_penalty": "输出不能为空"}
    
    text = response_text.strip()
    
    if expected_format == "json":
        # 尝试提取JSON
        if '{' in text and '}' in text:
            try:
                json.loads(text[text.index('{'):text.rindex('}')+1])
                return {"valid": True, "cleaned": text[text.index('{'):text.rindex('}')+1], "reason": "ok", "retry_penalty": ""}
            except json.JSONDecodeError:
                # 可能有多余文本,尝试找最长有效JSON
                for i in range(len(text)):
                    if text[i] == '{':
                        for j in range(len(text)-1, i, -1):
                            if text[j] == '}':
                                try:
                                    json.loads(text[i:j+1])
                                    return {"valid": True, "cleaned": text[i:j+1], "reason": "ok_extracted", "retry_penalty": ""}
                                except:
                                    continue
        return {"valid": False, "cleaned": text, "reason": "不是有效JSON", "retry_penalty": "只输出JSON对象本身,不要其他文字"}
    
    elif expected_format == "python_code":
        # 提取Python代码
        if '```python' in text:
            code = text.split('```python')[1].split('```')[0]
        elif '```' in text:
            code = text.split('```')[1]
        else:
            code = text
        
        # 去掉前置非代码行(如"以下是..." "我们被问到...")
        lines = code.split('\n')
        clean_lines = []
        started = False
        for line in lines:
            if not started and (line.startswith('def ') or line.startswith('class ') or line.startswith('import ') or line.startswith('from ') or line.strip() == ''):
                if line.strip() == '' and not started:
                    continue
                started = True
            if started or line.startswith('def ') or line.startswith('class '):
                started = True
                clean_lines.append(line)
        
        if not started:
            # 没找到def/class→全部作为代码
            clean_lines = lines
        
        cleaned = '\n'.join(clean_lines)
        if len(cleaned) > 10 and ('def ' in cleaned or 'import ' in cleaned or 'print' in cleaned):
            return {"valid": True, "cleaned": cleaned, "reason": "ok", "retry_penalty": ""}
        else:
            return {"valid": False, "cleaned": text, "reason": "无有效Python代码", "retry_penalty": "只输出Python代码,不要解释"}
    
    elif expected_format == "single_line":
        lines = [l for l in text.split('\n') if l.strip() and not l.startswith('```') and not l.startswith('我们')]
        if lines:
            return {"valid": True, "cleaned": lines[0].strip(), "reason": "ok", "retry_penalty": ""}
        return {"valid": False, "cleaned": text, "reason": "多行输出", "retry_penalty": "一句话,不要换行"}
    
    # any → 直接返回
    return {"valid": True, "cleaned": text, "reason": "ok", "retry_penalty": ""}


def build_penalty_prompt(original_prompt: str, last_error: str, retry_count: int) -> str:
    """构建带惩罚的prompt——告诉模型上次错了"""
    penalty = f"[系统提示: 上次输出未通过验证。原因: {last_error}。这是第{retry_count}次重试。严格按照要求格式输出。]"
    return f"{penalty}\n{original_prompt}"
