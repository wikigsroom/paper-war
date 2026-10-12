# 当前测试与历史结果

当前3.0报告在output/qa/godot/v3-*及v3/validation-index.json，输入SHA与当前运行文件核对。tests目录内既有JSON属于较早版本或中间失败的保留记录；不以它们代替最新验收，也不覆盖研究目录的历史审计。

规则与实体：test_simulation、test_world_foundation、test_world_combat。空间与经济：test_map_transport、test_theatre_decisions、test_theatre_economy。完整自动对战：test_campaign_play、test_challenges。原生指针与代表画面：theatre_ui_qa。完整正常预算GPU对局：record_theatre_battle。

运行规则检查时使用--output指定新JSON绝对路径；test_theatre_economy则直接将输出绝对路径作为用户参数。原生UI及对战录像必须用--profile-path隔离档案。录制器--level可选真实关卡，默认W04；不会赋予额外金币、科技、生命或兵力。

旧test_campaign_paths是2.0编组路径，不作为3.0规则证据。所有自动玩家、夹具、静音离线取帧与Android真机、人工胜率、实测帧率有明确边界，见当前地图重做报告。
