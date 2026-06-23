    # ═══ 超级直觉桥：独立接口(main非pulse), 由网格引擎计划接管 ═══
    if cycle_num > 0:
        try:
            import importlib as _il
            import super_intuition_bridge as _sib
            _il.reload(_sib)
            _sib.main()
            _si_state = CLUSTER / "super_intuition_state.json"
            if _si_state.exists():
                _si_str = _si_state.read_text()
                _si = __import__('json').loads(_si_str)
                if isinstance(_si, dict):
                    log(f"  直觉桥: 评分{_si.get('intuition_score',0):.3f} gap={_si.get('intuition_gap',0):.3f} {_si.get('pulse_count',0)}脉冲")
                else:
                    log(f"  直觉桥: ⚠️ 状态文件格式异常(type={type(_si).__name__}), 跳过")
        except Exception as e:
            import traceback as _tb
            _tb_str = "".join(_tb.format_exception(type(e), e, e.__traceback__))[:300]
            log(f"  直觉桥: ⚠️ {_tb_str}")
