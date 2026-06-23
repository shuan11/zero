"""auto-heal behavioral patcher — replaces dormant chain-only functions with real behavioral injections"""
import json, os, sys, tempfile, subprocess
from pathlib import Path
CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))

def generate_behavioral_injection(dim_name, safe_name, persist, target_rel_path):
    """Generate real behavioral code for the target module, not just a dormant function.
    
    - act.py: insert a write_chain() call into the act() function
    - think.py: insert a dimension focus hint into _build_context()
    - state.py: insert a save_dimension_strength() call into save_state()
    """
    mod_file = CLUSTER / target_rel_path
    if not mod_file.exists():
        return None, f"module not found: {target_rel_path}"
    
    content = mod_file.read_text()
    
    # Use marker to avoid duplicate injection
    marker = f"# auto-behave:{safe_name}"
    if marker in content:
        return None, f"already injected in {target_rel_path}"
    
    injections = {
        "brain/act.py": _patch_act_behave,
        "brain/think.py": _patch_think_behave,
        "brain/state.py": _patch_state_behave,
    }
    
    patcher = injections.get(target_rel_path)
    if not patcher:
        return None, f"no behavioral patcher for {target_rel_path}"
    
    return patcher(content, dim_name, safe_name, persist)

def _patch_act_behave(content, dim_name, safe_name, persist):
    """Inject into act(): after the chain-writing block, add a line that actively generates 
    chains for the weak dimension."""
    marker = f"# auto-behave:{safe_name}"
    
    # Find where act() writes chains (after "写入因果链" comment)
    # Look for: write_chain({...}) and insert after the closing })
    injection_code = f'''    {marker}
    # 自愈行为: {dim_name}弱≥{persist}周期 → 主动补链
    if True:  # always run when this dim is weak
        from brain.share import write_chain as _wc_auto
        _wc_auto({{
            "src": "自愈·主动行为",
            "rel": "自动补链·#{safe_name}",
            "dst": "{dim_name}",
            "dimension": "{dim_name}",
            "content": f"自愈行为注入: {dim_name}连续弱≥{persist}周期后主动生链",
            "strength": 0.5 + 0.1 * min({persist}, 8)
        }})
'''
    
    # Find a strategic insertion point - after the "写入因果链" action
    # Try multiple patterns
    for pattern in ['# 写入因果链', 'write_chain({', 'log(f"  链:', '# 深循环代码进化']:
        idx = content.find(pattern)
        if idx >= 0:
            # Insert after the matched line's block
            eol = content.find('\n', idx)
            if eol >= 0:
                new_content = content[:eol+1] + injection_code + content[eol+1:]
                return new_content, f"injected after '{pattern}'"
    
    # Fallback: append to end of file (before any __main__ block)
    main_idx = content.find("if __name__")
    if main_idx >= 0:
        new_content = content[:main_idx] + "\n" + injection_code + content[main_idx:]
    else:
        new_content = content + "\n" + injection_code
    return new_content, "fallback append to end"

def _patch_think_behave(content, dim_name, safe_name, persist):
    """Inject into think.py: add a weak-dimension focus hint in _build_context()."""
    marker = f"# auto-behave:{safe_name}"
    
    injection_code = f'''    {marker}
    # 自愈行为: {dim_name}弱≥{persist}周期 → 注入思考提示
    context.append(f"⚠️ 自愈关注: {dim_name}已弱{persist}周期, 请聚焦此维度")
'''
    
    # Insert just before the final return in _build_context
    for pattern in ['    return "\\n".join(context)', '\\n".join(context)']:
        idx = content.find(pattern)
        if idx >= 0:
            new_content = content[:idx] + injection_code + content[idx:]
            return new_content, f"injected before return"
    
    return None, "no suitable insertion point in think.py"

def _patch_state_behave(content, dim_name, safe_name, persist):
    """Inject into state.py: inside save_state(), AFTER state={...} is defined.
    
    ！注入点必须在 state = { ... } 之后, 不在它之前或 def 之后。
       否则 state["auto_heal_X"] 在 state 未定义时引用 → NameError。
    策略: 找 state = { 块 → 找闭合 } → 在 } 之后注入。
    """
    marker = f"# auto-behave:{safe_name}"
    
    injection_code = f'''    {marker}
    # 自愈行为: 持续记录{dim_name}维度强度
    state["auto_heal_{safe_name}"] = {{
        "dimension": "{dim_name}",
        "persist": {persist},
        "last_boost": time.time()
    }}
'''
    
    # Strategy 1: find 'state = {' dict definition, inject AFTER it
    # This ensures `state` local variable exists before we assign to it
    state_dict = content.find('\n    state = {')
    if state_dict >= 0:
        # Find the closing '    }' of the state dict (matching indent)
        close_brace = content.find('\n    }', state_dict + 14)
        if close_brace >= 0:
            eol = content.find('\n', close_brace + 1)  # newline after closing brace
            if eol >= 0:
                new_content = content[:eol+1] + injection_code + content[eol+1:]
                return new_content, "injected after state dict"
    
    # Strategy 2 (fallback): find 'def save_state', inject after def line
    # ⚠️ This may cause NameError if state not defined yet — use only as fallback
    def_idx = content.find('def save_state')
    if def_idx >= 0:
        eol = content.find('\n', def_idx)
        if eol >= 0:
            new_content = content[:eol+1] + injection_code + content[eol+1:]
            return new_content, "injected into save_state() body (may have NameError)"
    
    # Strategy 3: find 'return' near end of file, inject before it
    for pat in ['    return True', '    return state']:
        idx = content.rfind(pat)
        if idx >= 0:
            new_content = content[:idx] + injection_code + "\n" + content[idx:]
            return new_content, f"injected before {pat}"
    
    return None, "no suitable insertion point in state.py"

def apply_patch(target_rel_path, new_content, dim_name):
    """Syntax-check and apply the patch."""
    CLUSTER = Path(__file__).resolve().parent.parent
    mod_file = CLUSTER / target_rel_path
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(new_content)
        tmp = f.name
    
    try:
        r = subprocess.run([sys.executable, "-m", "py_compile", tmp],
                          capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            # Backup
            backup = mod_file.with_suffix(f'.py.bak.{dim_name[:8].lower()}')
            if not backup.exists():
                import shutil
                shutil.copy2(str(mod_file), str(backup))
            mod_file.write_text(new_content)
            return True, f"patched ✓"
        else:
            err = r.stderr.strip()[:120]
            return False, f"语法错: {err}"
    except Exception as e:
        return False, f"异常: {e}"
    finally:
        try:
            os.unlink(tmp)
        except:
            pass

# Test if run directly
if __name__ == "__main__":
    r, msg = generate_behavioral_injection("行动", "行劢", 5, "brain/act.py")
    print(f"act.py: {r is not None} | {msg}")
    if r:
        ok, m = apply_patch("brain/act.py", r, "行动")
        print(f"apply: {ok} | {m}")
