extends RefCounted

func research_notice(event: Dictionary) -> String:
	var notice: String="已解锁："+name_of(str(event.id))
	var reward: float=float(event.get("mana_reward",0))
	if reward>0:
		notice+=" · 研究回法"+(" +"+String.num(reward,1).trim_suffix(".0") if reward>=.1 else " · 少量法力")
	return notice

var FACTIONS: Array = []
var FACTION_NAMES: Dictionary = {}
var FACTION_COLORS: Dictionary = {}
const UNIT_ORDER = {"yin":["axe","spear","hammer","cannon","worker"],"mo":["blade","needle","priest","giant","worker"],"deng":["mirror","fire","shadow","effigy","worker"]}
const SPELL_ORDER = {"yin":["repair","lightning","cold","fury","stamp"],"mo":["sacrifice","bind","poison","convert","burst"],"deng":["protect","clone","fire","root","guardian"]}
const COMBAT_ROSTER_MAX = 4
const NAMES = {
"axe":"折斧兵","spear":"纸矛手","hammer":"压印锤卫","cannon":"卷轴炮车","worker":"运金纸工",
"blade":"墨刃猎兵","needle":"墨针手","priest":"拾纸祭司","giant":"纸巨人","thrall":"纸骨兵",
"mirror":"镜符刀卫","fire":"火签","shadow":"折影客","effigy":"厚纸俑","guardian":"护符纸卫",
"repair":"补纸","lightning":"雷印","cold":"寒纸风","fury":"振甲","stamp":"落印",
"sacrifice":"献纸","bind":"墨缚","poison":"腐墨","convert":"夺印","burst":"泼墨",
"protect":"护符","clone":"复印","root":"定字符","mana-1":"回法 · 一阶","mana-2":"回法 · 二阶","tower":"纸哨塔","mana":"产法纸灯"}
const SPELL_HINTS = {
"repair":"点击友军，恢复 85 生命。","lightning":"点击敌军，直击 110 伤害；无法反弹。",
"cold":"点击战场，让范围敌军缓行 3 秒。","fury":"点击友军，4 秒内伤害提升 40%。",
"stamp":"点击战场，0.55 秒后落印，范围 135 伤害。",
"sacrifice":"点击自己的战斗单位，以剩余生命的 18% 换取法力；工人与召唤物不可献纸。",
"bind":"点击敌军，禁止移动和攻击 2.3 秒。","poison":"点击战场，范围持续腐墨，每秒 12 伤害。",
"convert":"点击敌军，将其收为己方；工人、召唤物与复制体不可夺印。","burst":"点击战场，范围 110 伤害。",
"protect":"点击友军，免受伤害 2.5 秒。","clone":"点击自己的战斗单位，复制体存在 10 秒；巨人与复制体不能再复制。",
"fire":"点击战场，连续三道火签，每道 36 伤害。","root":"点击敌军，定身 2.8 秒，但其仍可攻击。",
"guardian":"点击战场，召唤存在 8 秒的纸卫；最多两名，不能直接放进敌基地。"}
const UNIT_HINTS = {
"axe":"耐打前排，护住纸矛和炮车。","spear":"中程投矛，需由前排保护。","hammer":"蓄力范围重击，短暂打断敌人。","cannon":"远程攻城，建筑伤害 ×2.5。",
"worker":"在矿点采金并运回基地；归仓时才获得金币。","blade":"近战猎兵，可短距扑向敌人。","needle":"墨针叠加持续腐蚀。","priest":"在附近消费阵亡纸标，折回纸骨兵。","giant":"大范围重击，前摇容易被打断。",
"mirror":"每 3 秒可反弹一次纸质投射物。","fire":"两连火签，输出后需要换签。","shadow":"最多越过 3.6 距离的前排，突击后排。","effigy":"厚纸甲使物理受伤减少 25%。"}

var balance: Dictionary
var unit_actions: Dictionary
var unit_frames: Dictionary={}
var unit_migration: Dictionary={}
var technology: Dictionary
var assets: Dictionary
var campaign: Array
var factions: Dictionary = {}
var maps: Dictionary = {}
var map_aliases: Dictionary = {}
var story: Dictionary = {}
var campaign_narrative: Dictionary = {}
var deployments: Dictionary = {}
var textures: Dictionary = {}
var texture_limit: int=140
var unit_atlas_limit: int=18
var texture_age: Dictionary={}
var texture_clock: int=0

func _init():
	balance = read_json("res://data/balance-prototype.json")
	unit_actions = read_json("res://data/unit-actions.json").profiles
	if FileAccess.file_exists("res://data/unit-frames.json"):unit_frames=read_json("res://data/unit-frames.json").profiles
	if FileAccess.file_exists("res://data/unit-id-migration.json"):unit_migration=read_json("res://data/unit-id-migration.json").aliases
	technology = read_json("res://data/technology.json")
	assets = read_json("res://data/assets.json").assets
	campaign = read_json("res://data/campaign.json").levels
	var world: Dictionary = read_json("res://data/factions.json")
	FACTIONS = world.order
	for f in world.factions:
		factions[f.id] = f
		FACTION_NAMES[f.id] = f.name
		FACTION_COLORS[f.id] = Color(f.color)
	var map_data: Dictionary = read_json("res://data/maps.json")
	map_aliases = map_data.aliases
	for map_def in map_data.maps: maps[map_def.id] = map_def
	story = read_json("res://data/story.json")
	campaign_narrative=read_json("res://data/campaign-narrative.json").profiles
	# The release manifest explicitly binds all units and shared spell-family icons.
	for id in balance.units.keys()+balance.spells.keys()+balance.buildings.keys():
		assert(assets.has(id),"Missing runtime asset: "+str(id))

func read_json(path: String):
	return JSON.parse_string(FileAccess.get_file_as_string(path))

func spell_hint(id: String) -> String:
	return str(balance.spells.get(id,{}).get("hint",SPELL_HINTS.get(id.get_slice(".",2),"")))

func name_of(id: String) -> String:
	if balance.spells.has(id):return str(balance.spells[id].get("name",NAMES.get(id.get_slice(".",2),id)))
	if balance.units.has(id): return str(balance.units[id].get("name",NAMES.get(id.get_slice(".",2),id)))
	if factions.has(id): return str(factions[id].name)
	if maps.has(id): return str(maps[id].name)
	if balance.upgrades.has(id): return str(balance.upgrades[id].get("name",NAMES.get(id.get_slice(".",2),id)))
	var tail = id.get_slice(".", id.get_slice_count(".")-1)
	if id == "unit.deng.fire": return "火签手"
	if id == "spell.deng.fire": return "火签雨"
	if id == "spell.deng.guardian": return "唤纸卫"
	if id == "unit.mo.worker": return "拾金纸工"
	if id == "unit.deng.worker": return "灯金纸工"
	return NAMES.get(tail,tail)

func unit_ids(faction: String) -> Array:
	var out: Array = normalize_roster(faction,deployments.get(faction,factions[faction].default_roster))
	out.append("unit."+faction+".worker")
	return out

func normalize_roster(faction: String, requested: Array, available: Array = [], limit: int = COMBAT_ROSTER_MAX) -> Array:
	var allowed: Array = all_unit_ids(faction) if available.is_empty() else available
	var out: Array = []
	limit=clampi(limit,2,COMBAT_ROSTER_MAX)
	for id in requested:
		if out.size()>=limit:break
		id=unit_migration.get(id,id)
		if allowed.has(id) and all_unit_ids(faction).has(id) and not out.has(id):out.append(id)
	if out.size()>=2:return out
	for id in factions[faction].default_roster+allowed:
		if out.size()>=mini(2,limit):break
		if allowed.has(id) and all_unit_ids(faction).has(id) and not out.has(id):out.append(id)
	return out

func all_unit_ids(faction: String) -> Array:
	return factions[faction].combat_units.duplicate()

func mana_hint(faction: String) -> String:
	return {"upgrade":"购买永久回法升级，重甲承受物理攻击。","sacrifice":"献弃真实兵力换法，攻击吸取生命。","facility":"完工纸灯持续供法，灯旁部队抵抗法术。","construction":"每座设施首次完工回法，设施旁部队伤害提高。","junction":"真实部队首次经过路口回法并加速。","delivery":"真实归仓货物回法，击倒真实敌兵获得赏金。","growth":"受伤部队自然修复回法，腐蚀会压制修复。","control":"成功控制敌军回法，每个单位有回法间隔。","damage":"真实军团承受敌方伤害回法，残血部队奋战。","research":"完成研究回法，部队抵抗法术但怕物理攻击。"}.get(factions[faction].mana,"")

func map_definition(id: String) -> Dictionary:
	return maps.get(map_aliases.get(id,id),maps.values()[0])

func unit_hint(id: String) -> String:
	return str(balance.units[id].get("hint",UNIT_HINTS.get(id.get_slice(".",2),"负责归仓运输；暴露在前线时可能丢失货物。")))

func spell_ids(faction: String) -> Array:
	var out = []
	for id in balance.spells:
		if id.get_slice(".",1)==faction: out.append(id)
	return out

func texture(path: String) -> Texture2D:
	texture_clock+=1
	if not textures.has(path):
		if path.begins_with("res://assets/animation/frames-v1/") and path.ends_with("-atlas.png"):
			var atlas_keys: Array=textures.keys().filter(func(key):return str(key).begins_with("res://assets/animation/frames-v1/") and str(key).ends_with("-atlas.png"))
			if atlas_keys.size()>=unit_atlas_limit:
				atlas_keys.sort_custom(func(a,b):return int(texture_age.get(a,0))<int(texture_age.get(b,0)))
				textures.erase(atlas_keys[0]);texture_age.erase(atlas_keys[0])
		while textures.size()>=texture_limit:
			var oldest: String=textures.keys()[0]
			for key in textures:
				if int(texture_age.get(key,0))<int(texture_age.get(oldest,0)):oldest=key
			textures.erase(oldest);texture_age.erase(oldest)
		textures[path] = load(path)
	texture_age[path]=texture_clock
	return textures[path]

func release_unit_atlases():
	for path in textures.keys():
		if str(path).begins_with("res://assets/animation/frames-v1/") and str(path).ends_with("-atlas.png"):
			textures.erase(path);texture_age.erase(path)

func art(id: String, portrait: bool = false) -> Texture2D:
	if not assets.has(id): return null
	return texture(assets[id].get("portrait",assets[id].path) if portrait else assets[id].path)

func tech(id: String) -> Dictionary:
	for node in technology.nodes:
		if node.id == id: return node
	return {}

func tech_for(grant: String) -> Dictionary:
	for node in technology.nodes:
		if node.grant == grant: return node
	return {}
