extends Node2D

const TheatreGround = preload("res://scripts/theatre_ground.gd")
const GroundCache = preload("res://scripts/theatre_ground_cache.gd")
const UITheme = preload("res://scripts/ui_theme.gd")
var ground_mesh_cache=GroundCache.new()
var profile_draw_layers: bool=OS.get_cmdline_user_args().has("--qa-profile-layers")
var layer_cpu_us: Dictionary={}
var paper_ellipse_mesh: ArrayMesh
var ownership_meshes: Array[ArrayMesh]=[]
var draw_visibility_cache: Dictionary={}
var unit_atlas_cache: Dictionary={}
var unit_height_cache: Dictionary={}
var unit_height_cache_scale: float=-1.0
var render_point_cache: Dictionary={}
var render_point_refs: Dictionary={}
var ordered_units_cache: Array=[]
var ordered_units_sources: Array=[]
var ordered_units_tick: int=-1
var draw_visibility_revision: int=-1
var draw_visibility_side: int=-1
const FramePlayer = preload("res://scripts/unit_frame_player.gd")
const TheatreFog = preload("res://scripts/theatre_fog.gd")
var theatre_fog=TheatreFog.new()

var db
var player_side: int=0
var sim
var camera_x: float = 10.0
var target_camera: float = 10.0
var follow_front: bool = false
var direct_pan: bool = false
var selected_spell: String = ""
var selected_building: String = ""
var pointer: Vector2 = Vector2.ZERO
var selected_uid: int = 0
var particles: Array = []
var effects: Array = []
var floats: Array = []
var hit_holds: Dictionary = {}
var economy_warning: Dictionary = {}
var canvas_shift: Vector2=Vector2.ZERO
var visual_time: float = 0
var shake: float = 0
var reduced_motion: bool = false
var menu: bool = true
var menu_characters: bool = true
var width: float = 1600
var height: float = 900
var mobile_ui: bool = false
var mobile_playfield: Rect2
var mobile_minimap: Rect2
var mobile_pointer_active: bool=false
var mobile_floor: float=630
var desktop_playfield: Rect2
var desktop_minimap: Rect2
var desktop_floor: float=630
var particle_budget: int=650
var effect_budget: int=160
var float_budget: int=160
var font: Font
var event_ground_y: float = 0
const PX = 112.0
const PY = 64.0
const PUPPET_SCALE = .78
const PAPER = Color("e8deca")
const INK = Color("343332")
const MANA = Color("397e9e")

func _ready():
	texture_repeat=CanvasItem.TEXTURE_REPEAT_ENABLED
	var variation=FontVariation.new()
	variation.base_font=load("res://assets/fonts/NotoSansSC.ttf")
	variation.variation_opentype={"wght":500.0}
	font=variation

func floor_y() -> float:
	if mobile_ui and mobile_playfield.has_area():return mobile_floor
	if not menu and desktop_playfield.has_area():return desktop_floor
	return height*.70

func playfield_rect() -> Rect2:
	if mobile_ui:return mobile_playfield
	return desktop_playfield if desktop_playfield.has_area() else Rect2(0,64,width,height-220)

func world_to_screen(x: float, lane: float = 0.0, ground_y: float = NAN) -> Vector2:
	if is_nan(ground_y): ground_y=0.0 if sim==null or menu else sim.map.ground_y_at(x)
	return Vector2(width*.5+(x-camera_x)*PX,floor_y()+ground_y*PY+lane)

func point_to_screen(x: float,y: float) -> Vector2:
	return world_to_screen(x,0,y)

func screen_to_ground(pos: Vector2) -> Dictionary:
	return sim.map.project(Vector2(screen_to_world(pos.x),(pos.y-floor_y())/PY))

func screen_to_world(x: float) -> float:
	return (x-width*.5)/PX+camera_x

func reset(battle):
	ground_mesh_cache.clear_terrain()
	sim=battle; menu=false; camera_x=minf(width/PX*.5,sim.map.length*.5); target_camera=camera_x
	direct_pan=false
	follow_front=false; particles.clear(); effects.clear(); floats.clear();hit_holds.clear()
	economy_warning.clear()
	draw_visibility_cache.clear();draw_visibility_revision=-1;draw_visibility_side=-1
	unit_atlas_cache.clear()
	unit_height_cache.clear();unit_height_cache_scale=-1.0
	render_point_cache.clear();render_point_refs.clear()
	ordered_units_cache.clear();ordered_units_sources.clear();ordered_units_tick=-1
	selected_spell=""; selected_building=""; selected_uid=0; shake=0

func update(delta: float, paused: bool = false):
	# Simulation dictionaries are mutable; never carry a projected point across
	# a frame boundary. Within one frame this cache removes duplicate projections
	# from depth sorting, unit overlays and effect anchors.
	render_point_cache.clear();render_point_refs.clear()
	width=get_viewport_rect().size.x/scale.x; height=get_viewport_rect().size.y/scale.y
	if not paused or menu:visual_time+=delta
	if not menu and sim!=null and follow_front: target_camera=sim.front(player_side)
	var map_length: float = 56 if menu or sim==null else sim.map.length
	var half_view: float = minf(width/PX*.5,map_length*.5)
	target_camera=clampf(target_camera,half_view,map_length-half_view)
	camera_x=target_camera if direct_pan else lerpf(camera_x,target_camera,1-exp(-delta*7))
	shake=maxf(0.0,shake-delta*28)
	if not paused:
		if not economy_warning.is_empty():
			economy_warning.left-=delta
			if economy_warning.left<=0:economy_warning.clear()
		for uid in hit_holds.keys():
			hit_holds[uid].left-=delta
			if hit_holds[uid].left<=0:hit_holds.erase(uid)
		var alive: int=0
		for p in particles:
			p.life-=delta; p.v.y+=delta*480; p.pos+=p.v*delta; p.angle+=p.spin*delta
			if p.life>0:particles[alive]=p;alive+=1
		particles.resize(alive)
		alive=0
		for e in effects:
			e.life-=delta
			if e.life>0:effects[alive]=e;alive+=1
		effects.resize(alive)
		alive=0
		for f in floats:
			f.life-=delta
			if f.life>0:floats[alive]=f;alive+=1
		floats.resize(alive)
	queue_redraw()

func on_event(e: Dictionary):
	if sim!=null and not sim.event_visible(player_side,e):return
	while floats.size()>=float_budget:floats.pop_front()
	event_ground_y = float(e.get("y",0))
	var kind=e.kind
	var x=float(e.get("x",0))
	e["visual_dx"]=0.0
	var color=db.FACTION_COLORS.get(sim.players[int(e.get("side",0))].faction,INK)
	match kind:
		"economy_alarm":economy_warning={"x":x,"y":event_ground_y,"left":6.0}
		"hit":
			var unit=sim.actor(int(e.uid))
			if not unit.is_empty() and not unit.get("building",false): hit_holds[e.uid]={"left":.055,"walk":unit.walk,"pose":unit.duplicate(true)}
			if absf(x-camera_x)<13:
				shards(x,6 if e.heavy else 3,color,0.35 if e.heavy else .23,90 if e.heavy else 55,float(e.visual_dx))
				add_effect("hit",x,.16,color,e)
				if e.heavy: shake=maxf(shake,5)
				if float(e.amount)>=4: floats.append({"x":x,"dx":e.visual_dx,"ground_y":event_ground_y,"text":str(int(ceilf(e.amount))),"life":.7,"total":.7,"color":Color("b74532"),"y":-100-float(e.uid%3)*18})
		"death":
			shards(x,15,color,.75,155,float(e.visual_dx))
			add_effect("death",x,.85,color,e)
		"building_death": shards(x,35,color,1.2,225); shake=maxf(shake,12); add_effect("blast",x,.7,color,e)
		"attack":
			hit_holds.erase(int(e.uid))
			var profile: Dictionary=db.unit_actions[e.id]
			var shooter: Dictionary=sim.actor(int(e.uid))
			if not shooter.is_empty() and e.ranged:
				var origin: Vector2=action_tip(shooter)
				for missile in sim.projectiles:
					if not missile.get("observed_only",false) and int(missile.source)==int(e.uid) and not missile.has("render_dx"):
						var foot: Vector2=point_to_screen(missile.start_x,missile.start_y)
						missile["render_dx"]=origin.x-foot.x;missile["render_dy"]=origin.y-foot.y
			add_effect("weapon_release",x,.28,color,Dictionary(e).merged({"gesture":profile.gesture,"projectile":profile.projectile}))
		"cast":
			var tail=e.id.get_slice(".",2)
			add_effect(tail,x,.65,color,e)
			shards(x,14,MANA,.65,110)
		"impact": add_effect(e.fx,x,.5,color,e); shards(x,25,color,.65,210); shake=maxf(shake,8)
		"heal":
			floats.append({"x":x,"ground_y":event_ground_y,"text":"+"+str(int(e.amount)),"life":1.0,"total":1.0,"color":Color("377b78"),"y":-130})
		"gold":
			if int(e.side)==player_side: floats.append({"x":x,"ground_y":event_ground_y,"text":"+"+str(int(e.amount)),"life":.8,"total":.8,"color":Color("a58137"),"y":-65})
		"mine_strike":
			if absf(x-camera_x)<13:
				add_effect("mine_strike",x,.32,Color("c39539"),e)
		"cargo_loaded":
			if absf(x-camera_x)<13:add_effect("cargo_loaded",x,.35,Color("c39539"),e)
		"dash": add_effect("dash",x,.3,color,e)
		"summon","spawn","build": add_effect("summon",x,.45,color,e)
		"building_completed":add_effect("protect",x,.5,Color("397e9e"),e);shards(x,12,PAPER,.6,80)
		"facility_disabled":floats.append({"x":x,"ground_y":event_ground_y,"text":"封禁","life":1.0,"total":1.0,"color":MANA,"y":-120})
		"chain":
			add_effect("lightning",x,.3,MANA,e)
		"unit_special":add_effect("unit_special",x,.45,color,e)
		"reflect","blocked": add_effect("protect",x,.3,Color("b9964f"),e)
		"interrupt": floats.append({"x":x,"ground_y":event_ground_y,"text":"打断","life":.8,"total":.8,"color":MANA,"y":-165})

func add_effect(type: String, x: float, life: float, color: Color, data: Dictionary):
	if effects.size()>=effect_budget: effects.pop_front()
	effects.append({"type":type,"x":x,"y":data.get("y",0),"life":life,"total":life,"color":color,"data":data.duplicate()})

func shards(x: float, count: int, color: Color, life: float, force: float, visual_dx: float=0):
	if mobile_ui:count=maxi(1,int(ceilf(count*(.45 if particle_budget<150 else .7))))
	for i in range(count):
		if particles.size()>=particle_budget: particles.pop_front()
		var seed_angle=float((i*67+int(x*13))%360)*PI/180.0
		particles.append({"pos":Vector2(x*PX+visual_dx,event_ground_y*PY-95),"v":Vector2(cos(seed_angle)*force,-absf(sin(seed_angle))*force-40),"life":life,"total":life,"color":color if i%3 else PAPER,"angle":seed_angle,"spin":cos(seed_angle)*7,"size":3.0+float(i%4)})

func tint(color: Color, alpha: float) -> Color:
	return Color(color.r,color.g,color.b,alpha)

func draw_night_lanterns():
	# Small warm pools give the dark paper stage the approved lantern language
	# without revealing actors or changing simulation visibility.
	var anchors: Array=[]
	if menu:
		anchors=[Vector2(width*.12,floor_y()-22),Vector2(width*.42,floor_y()-18)]
	elif sim!=null:
		for base in sim.bases:
			var p: Vector2=point_to_screen(float(base.x),float(base.y))-Vector2(0,74)
			if p.x>-90 and p.x<width+90:anchors.append(p)
	for p in anchors:
		draw_circle(p,46,Color(UITheme.LANTERN,.035))
		draw_circle(p,24,Color(UITheme.LANTERN,.075))
		draw_rect(Rect2(p-Vector2(5,11),Vector2(10,22)),Color(UITheme.LANTERN,.78))
		draw_line(p+Vector2(-8,-12),p+Vector2(8,-12),Color(UITheme.GOLD,.8),2,true)

func _draw():
	if db==null: return
	render_point_cache.clear();render_point_refs.clear()
	draw_visibility_cache.clear()
	draw_visibility_revision=int(sim.visibility.revision) if sim!=null and sim.visibility!=null else -1
	draw_visibility_side=player_side
	var profile_mark: int=Time.get_ticks_usec() if profile_draw_layers else 0
	canvas_shift=Vector2.ZERO
	draw_rect(Rect2(0,0,width,height),PAPER)
	var map_id="lantern-ridge" if menu or sim==null else sim.map.definition.theme
	# The selected direction supplies one reviewed night plate for the title and
	# default stamp-plain stage. Other regions retain their authored silhouettes
	# so map identity remains legible across the campaign.
	var use_night_backdrop: bool=UITheme.NIGHT_LANTERN and (menu or map_id=="stamp-plain")
	var bg: Texture2D=db.art("background.night-lantern") if use_night_backdrop else db.art("background."+map_id)
	if bg==null: bg=db.art("background.stamp-plain")
	var offset=(camera_x-28)*5
	var backdrop_modulate: Color=Color.WHITE if use_night_backdrop else UITheme.NIGHT_SCENE_MODULATE
	draw_texture_rect(bg,Rect2(-100-offset,-40 if menu else 80,width+200,height*.85),false,backdrop_modulate)
	# The source backdrops are daytime paper paintings. A cool wash gives every
	# scene the approved moonlit depth while warm UI rails and lanterns remain
	# the readable focal accents.
	draw_rect(Rect2(0,0,width,height),Color(UITheme.MIDNIGHT,.08 if use_night_backdrop else .24))
	if menu and not menu_characters:draw_rect(Rect2(0,0,width,height),Color(PAPER,.66))
	var camera_shift=Vector2.ZERO
	if shake>0 and not reduced_motion and not direct_pan and not menu:camera_shift=Vector2(sin(visual_time*91),cos(visual_time*73))*shake
	canvas_shift=camera_shift
	draw_set_transform(camera_shift)
	if menu:
		draw_colored_polygon(PackedVector2Array([Vector2(0,floor_y()+6),Vector2(width,floor_y()+6),Vector2(width,height),Vector2(0,height)]),Color("5e4d42"))
		draw_line(Vector2(0,floor_y()+7),Vector2(width,floor_y()+7),UITheme.GOLD,3)
		draw_night_lanterns()
	elif sim!=null:
		ground_mesh_cache.draw_terrain(self,sim)
		# A translucent blue-black wash turns the paper terrain into the approved
		# moonlit stage while the unit layer below remains crisp and readable.
		draw_rect(Rect2(0,64,width,height-64),Color(UITheme.MIDNIGHT,.34))
		draw_night_lanterns()
	if profile_draw_layers:profile_mark=mark_draw_layer("background_ground",profile_mark)
	if menu:
		draw_menu_units(); draw_set_transform(Vector2.ZERO); return
	if sim==null: return
	# Fog belongs to the scene, before only legally observable actors and tags.
	# In particular a revealed lower-road soldier stays readable below a hidden bridge.
	theatre_fog.draw(self)
	if profile_draw_layers:profile_mark=mark_draw_layer("fog",profile_mark)
	for side in range(2):
		draw_building(sim.bases[side])
		for slot in range(sim.side_sites(side).size()):
			draw_site(side,slot)
	for mine_def in sim.map.definition.mines:
		var known: bool=sim.visibility.point_visible(player_side,mine_def)
		if not known:continue
		var mine=point_to_screen(mine_def.x,mine_def.y)
		var tex=db.art("resource.common.mine")
		if tex:draw_texture_rect(tex,Rect2(mine-Vector2(78,140*476.0/512.0),Vector2(156,140)),false)
		var state: Dictionary = sim.mine_state(mine_def) if known else {"active":0,"waiting":0}
		var occupancy: String="%d/%d"%[state.active,int(mine_def.capacity)] if known else "未知/%d"%int(mine_def.capacity)
		var text: String = ("我方 · " if int(mine_def.owner)==player_side else "敌方 · ")+str(mine_def.get("label","金矿"))+" "+occupancy
		if state.waiting>0:text+=" · 等%d"%state.waiting
		var mine_font: int=roundi(12/scale.x) if mobile_ui else 18
		var text_width: float = font.get_string_size(text,HORIZONTAL_ALIGNMENT_LEFT,-1,mine_font).x
		var padding: float=6.0/scale.x if mobile_ui else 6.0
		var tag: Rect2=field_tag_rect(Rect2(mine+Vector2(-text_width*.5-padding,12),Vector2(text_width+padding*2,22/scale.y if mobile_ui else 27)),mine)
		if tag.has_area():
			draw_rect(tag,tint(PAPER,.96))
			draw_string(font,tag.position+Vector2(padding,16/scale.y if mobile_ui else 20),text,HORIZONTAL_ALIGNMENT_LEFT,-1,mine_font,INK)
			if int(mine_def.owner)==player_side and sim.players[player_side].get("preferred_mine","")==mine_def.id:
				draw_line(tag.position+Vector2(0,tag.size.y+2),tag.end+Vector2(0,2),MANA,3,true)
	for side in [player_side]:
		for fork in sim.map.fork_nodes(side):
			if not location_visible_cached(float(fork.position[0]),float(fork.position[1])):continue
			var pos=point_to_screen(float(fork.position[0]),float(fork.position[1]))
			var color: Color = Color("4c8a91") if side==player_side else Color("c45c43")
			var edge: Dictionary = sim.map.edges[fork.selected]
			var selected_points=PackedVector2Array()
			for i in range(9):
				var distance: float = float(edge.length)*(i/8.0)*.4 if side==0 else float(edge.length)*(1-(i/8.0)*.4)
				var point: Vector2 = sim.map.point(fork.selected,distance)
				selected_points.append(point_to_screen(point.x,point.y))
			draw_polyline(selected_points,tint(color,.8),5,true)
			var tip: Vector2 = selected_points[-1];var direction: Vector2 = (tip-selected_points[-2]).normalized()
			draw_line(tip,tip-direction.rotated(.6)*16,color,3,true);draw_line(tip,tip-direction.rotated(-.6)*16,color,3,true)
	if sim.config.get("win","") in ["escort","intercept"]:
		var goal: Dictionary = sim.config.get("objective_anchor",sim.map.definition.objective_anchor)
		var pos=point_to_screen(goal.x,goal.y)
		draw_line(pos-Vector2(0,160),pos+Vector2(0,14),Color("b74532"),3,true)
		draw_string(font,pos-Vector2(49,170),"交接点" if sim.config.win=="escort" else "矿线",HORIZONTAL_ALIGNMENT_LEFT,-1,20,INK)
	for entrance in sim.config.get("enemy_entries",[]):
		if not sim.visibility.point_visible(player_side,entrance):continue
		var pos=point_to_screen(entrance.x,entrance.y)
		draw_line(pos,pos-Vector2(0,76),Color("b74532"),3,true)
		draw_colored_polygon(PackedVector2Array([pos-Vector2(0,76),pos+Vector2(53,-76),pos+Vector2(44,-47),pos-Vector2(0,47)]),Color("d85840"))
		draw_string(font,pos+Vector2(4,-54),"伏兵",HORIZONTAL_ALIGNMENT_LEFT,-1,18,PAPER)
	for b in sim.buildings: draw_building(b)
	for c in sim.corpses:
		if not location_visible_cached(float(c.x),float(c.y)):continue
		var pos=world_to_screen(c.x,5,c.y)
		draw_colored_polygon(PackedVector2Array([pos+Vector2(-13,0),pos+Vector2(6,-8),pos+Vector2(15,1),pos+Vector2(-2,5)]),Color(.91,.87,.79,c.left/8))
		draw_line(pos+Vector2(-5,-1),pos+Vector2(6,-1),Color(.4,.3,.26,c.left/8),2)
	if profile_draw_layers:profile_mark=mark_draw_layer("buildings_tags",profile_mark)
	var ordered=ordered_units()
	for u in ordered: draw_unit(u)
	if profile_draw_layers:profile_mark=mark_draw_layer("units",profile_mark)
	for zone in sim.spell_areas:draw_spell_zone(zone)
	for p in sim.projectiles: draw_projectile(p)
	draw_route_signs()
	for e in effects: draw_effect(e)
	if profile_draw_layers:profile_mark=mark_draw_layer("projectiles_effects",profile_mark)
	for p in particles:
		if not location_visible_cached(float(p.pos.x)/PX,(float(p.pos.y)+95)/PY):continue
		var pos=Vector2(width*.5+p.pos.x-camera_x*PX,floor_y()+p.pos.y)
		draw_set_transform(pos+camera_shift,p.angle)
		var c=tint(p.color,clampf(p.life/p.total*1.5,0,1))
		draw_colored_polygon(PackedVector2Array([Vector2(-p.size,-p.size*.4),Vector2(p.size,-p.size*.3),Vector2(p.size*.7,p.size*.5),Vector2(-p.size*.8,p.size*.6)]),c)
		draw_line(Vector2(-p.size,p.size*.6),Vector2(p.size*.7,p.size*.5),tint(INK,c.a*.4),1)
	draw_set_transform(camera_shift)
	for f in floats:
		if not location_visible_cached(float(f.x),float(f.get("ground_y",0))):continue
		var pos=world_to_screen(f.x,0,float(f.get("ground_y",0)))+Vector2(-12+float(f.get("dx",0)),f.y-(1-f.life/f.total)*42)
		draw_string(font,pos,f.text,HORIZONTAL_ALIGNMENT_LEFT,-1,24,tint(INK,f.life/f.total))
		draw_string(font,pos-Vector2(1,1),f.text,HORIZONTAL_ALIGNMENT_LEFT,-1,23,tint(f.color,f.life/f.total))
	draw_set_transform(Vector2.ZERO)
	draw_target_preview()
	if profile_draw_layers:mark_draw_layer("particles_numbers_preview",profile_mark)

func location_visible_cached(x: float,y: float) -> bool:
	# Cache only inside one draw pass. Fog revision and observer side remain live.
	var key:=Vector2(x,y)
	var revision: int=int(sim.visibility.revision) if sim!=null and sim.visibility!=null else -1
	if revision!=draw_visibility_revision or player_side!=draw_visibility_side:
		draw_visibility_cache.clear();draw_visibility_revision=revision;draw_visibility_side=player_side
	if not draw_visibility_cache.has(key):draw_visibility_cache[key]=sim.location_visible(player_side,x,y)
	return bool(draw_visibility_cache[key])

func ordered_units() -> Array:
	# Cache each physical Y once. Keep the original comparator, including its
	# approximate-height threshold and uid%5 ties, and the original input order.
	var actors: Array=sim.units
	var tick: int=int(sim.tick_count)
	if ordered_units_tick==tick and ordered_units_sources.size()==actors.size():
		var same_sources: bool=true
		for index in range(actors.size()):
			if not is_same(actors[index],ordered_units_sources[index]):same_sources=false;break
		if same_sources:return ordered_units_cache
	var heights: PackedFloat64Array=PackedFloat64Array()
	var ties: PackedByteArray=PackedByteArray()
	var indices: Array[int]=[]
	for index in range(actors.size()):
		heights.append(render_physical_point(actors[index]).y)
		ties.append(int(actors[index].uid)%5);indices.append(index)
	indices.sort_custom(func(a: int,b: int):return heights[a]<heights[b] if absf(heights[a]-heights[b])>.05 else ties[a]<ties[b])
	var ordered: Array=[]
	for index in indices:ordered.append(actors[index])
	ordered_units_sources.clear();ordered_units_sources.append_array(actors)
	ordered_units_tick=tick;ordered_units_cache=ordered
	return ordered_units_cache

func mark_draw_layer(label_value: String,started: int) -> int:
	var now: int=Time.get_ticks_usec()
	layer_cpu_us[label_value]=now-started
	return now

func field_tag_rect(rect: Rect2,anchor: Vector2) -> Rect2:
	var field: Rect2=playfield_rect()
	if not field.has_area():return Rect2()
	# Keep nearby anchored captions in the actual stage, clear of the corner
	# navigator and action strip. Distant signs must not stick to the screen edge.
	if not field.grow(44/scale.x).has_point(anchor):return Rect2()
	var bounds: Rect2=field.grow_individual(-8/scale.x,(-40 if mobile_ui else -8)/scale.y,-8/scale.x,(-8)/scale.y)
	if bounds.size.x<rect.size.x or bounds.size.y<rect.size.y:return Rect2()
	return Rect2(Vector2(clampf(rect.position.x,bounds.position.x,bounds.end.x-rect.size.x),clampf(rect.position.y,bounds.position.y,bounds.end.y-rect.size.y)),rect.size)

func route_sign_position(side: int,fork: Dictionary) -> Vector2:
	return route_sign_rect(side,fork).get_center()

func route_sign_rect(side: int,fork: Dictionary) -> Rect2:
	if not location_visible_cached(float(fork.position[0]),float(fork.position[1])):return Rect2()
	var foot: Vector2=point_to_screen(float(fork.position[0]),float(fork.position[1]))
	var position: Vector2=foot+Vector2(-44 if side==0 else 44,-176)
	if mobile_ui:return field_tag_rect(Rect2(position-Vector2(44,24)/scale,Vector2(88,48)/scale),foot)
	return field_tag_rect(Rect2(position-Vector2(48,22),Vector2(96,44)),foot)

func draw_route_signs():
	for side in [player_side]:
		for fork in sim.map.fork_nodes(side):
			if not location_visible_cached(float(fork.position[0]),float(fork.position[1])):continue
			var visual: Rect2=route_sign_rect(side,fork)
			if not visual.has_area():continue
			var foot=point_to_screen(float(fork.position[0]),float(fork.position[1]))
			var pos=visual.get_center()
			var color: Color = MANA if side==player_side else Color("c45c43")
			var role: String = sim.map.edges[fork.selected].get("route_role","ground")
			draw_line(foot,pos+Vector2(0,21),INK,3,true)
			if mobile_ui:visual=visual.grow_individual(0,-10/scale.y,0,-10/scale.y)
			draw_rect(visual,color)
			draw_rect(visual,PAPER,false,2)
			draw_string(font,pos+(Vector2(-36,5)/scale if mobile_ui else Vector2(-40,6)),("我" if side==player_side else "敌")+("纸桥" if role=="bridge" else "主路"),HORIZONTAL_ALIGNMENT_LEFT,-1,roundi(14/scale.x) if mobile_ui else 20,PAPER)

func draw_site(side: int,slot: int):
	# Do not consult a hidden opponent's occupied slots to choose the rendered sign.
	if not sim.visibility.point_visible(player_side,sim.slot_anchor(side,slot)):return
	for b in sim.buildings:
		if b.side==side and b.slot==slot and b.hp>0:return
	var anchor: Dictionary = sim.slot_anchor(side,slot)
	var pos=point_to_screen(anchor.x,anchor.y)
	if pos.x<-130 or pos.x>width+130:return
	var types: Array = anchor.get("types",["tower","mana"])
	var color: Color = MANA if types==["mana"] else Color("736056")
	var matching: bool = side==player_side and selected_building!="" and types.has(selected_building.get_slice(".",2))
	paper_ellipse(pos+Vector2(0,5),Vector2(28,8),tint(color,.22))
	draw_line(pos+Vector2(-24,5),pos+Vector2(24,5),color,3,true)
	draw_line(pos,pos-Vector2(0,35),color,3,true)
	draw_colored_polygon(PackedVector2Array([pos-Vector2(0,38),pos+Vector2(23,-38),pos+Vector2(18,-20),pos-Vector2(0,20)]),tint(PAPER,.96))
	draw_string(font,pos+Vector2(3,-23),"灯" if types==["mana"] else "塔" if types==["tower"] else "筑",HORIZONTAL_ALIGNMENT_LEFT,-1,15,color)
	var text: String = str(anchor.get("label","建造位"))
	var site_font: int=roundi(12/scale.x) if mobile_ui else 18
	var text_width: float = font.get_string_size(text,HORIZONTAL_ALIGNMENT_LEFT,-1,site_font).x
	var caption: Rect2=field_tag_rect(Rect2(pos+Vector2(-text_width*.5-5,13),Vector2(text_width+10,22/scale.y if mobile_ui else 26)),pos)
	if caption.has_area():
		draw_rect(caption,tint(PAPER,.96))
		draw_string(font,caption.position+Vector2(5,16/scale.y if mobile_ui else 20),text,HORIZONTAL_ALIGNMENT_LEFT,-1,site_font,color)
	if matching:
		var tex=db.art(selected_building)
		var size=Vector2(116,138)
		if tex:draw_texture_rect(tex,Rect2(pos-Vector2(size.x*.5,size.y*476.0/512.0),size),false,Color(1,1,1,.35))
		draw_arc(pos+Vector2(0,5),34,0,TAU,32,MANA,3,true)
		if selected_building.ends_with("tower"):
			var reach: float = float(db.balance.buildings[selected_building].get("range",0))
			for edge_id in sim.map.edges:
				var line=PackedVector2Array()
				for i in range(49):
					var p: Vector2 = sim.map.point(edge_id,float(sim.map.edges[edge_id].length)*i/48.0)
					if p.distance_to(Vector2(anchor.x,anchor.y))<=reach:line.append(point_to_screen(p.x,p.y)-Vector2(0,7))
					elif line.size()>1:draw_polyline(line,tint(MANA,.75),4,true);line.clear()
				if line.size()>1:draw_polyline(line,tint(MANA,.75),4,true)

func draw_menu_units():
	if not menu_characters:return
	for i in range(3):
		var f=["yin","mo","deng"][i]
		var tex=db.art(db.factions[f].core_roster[0])
		if tex:
			var size=Vector2(286,286)
			var pos=Vector2(180+float(i)*246,height*.82)
			paper_ellipse(pos+Vector2(0,2),Vector2(90,12),Color(0,0,0,.10))
			draw_texture_rect(tex,Rect2(pos-Vector2(size.x*.5,size.y*476.0/512.0),size),false)
	for i in range(0 if reduced_motion else 18):
		var x=fposmod(float(i)*101.2+visual_time*11,width)
		var y=150+fposmod(float(i)*47.0+sin(visual_time*.7+i)*12,450)
		draw_colored_polygon(PackedVector2Array([Vector2(x,y),Vector2(x+5,y-2),Vector2(x+8,y+3),Vector2(x+2,y+4)]),Color(.58,.44,.27,.13))

func paper_ellipse(center: Vector2, radius: Vector2, color: Color):
	if paper_ellipse_mesh==null:
		var points=PackedVector2Array();var vertices=PackedVector3Array();var colors=PackedColorArray()
		for i in range(24):
			var a: float=float(i)/24*TAU
			var p=Vector2(cos(a),sin(a));points.append(p);vertices.append(Vector3(p.x,p.y,0));colors.append(Color.WHITE)
		var arrays: Array=[];arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_COLOR]=colors;arrays[Mesh.ARRAY_INDEX]=Geometry2D.triangulate_polygon(points)
		paper_ellipse_mesh=ArrayMesh.new();paper_ellipse_mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	draw_mesh(paper_ellipse_mesh,null,Transform2D(Vector2(radius.x,0),Vector2(0,radius.y),center),color)

func draw_building(b: Dictionary):
	if not sim.visible_to(player_side,b):return
	var pos=point_to_screen(b.x,b.y)
	if pos.x<-280 or pos.x>width+280: return
	var tex=db.art(b.id)
	if tex==null: return
	var size=Vector2(286,290) if b.base else (Vector2(150,160) if b.id.ends_with("mana") else Vector2(170,220))
	paper_ellipse(pos+Vector2(0,5),Vector2(size.x*.42,16),Color(0,0,0,.14))
	var color=Color(1.7,1.55,1.4) if b.hurt>0 else Color.WHITE
	draw_texture_rect(tex,Rect2(pos-Vector2(size.x*.5,size.y*476.0/512.0),size),false,color)
	if b.get("state","")=="constructing":
		var progress: float = 1-float(b.construction)/maxf(.01,float(b.construction_total))
		draw_rect(Rect2(pos-Vector2(60,50),Vector2(120,12)),INK)
		draw_rect(Rect2(pos-Vector2(58,48),Vector2(116*progress,8)),Color("b9964f"))
		draw_string(font,pos-Vector2(48,64),"施工中",HORIZONTAL_ALIGNMENT_LEFT,-1,19,INK)
	if b.get("disabled",0)>0:draw_string(font,pos-Vector2(35,70),"熄台",HORIZONTAL_ALIGNMENT_LEFT,-1,23,Color("b74532"))
	if b.id.ends_with("mana"):
		var glow=pos-Vector2(0,105)
		draw_circle(glow,20+sin(visual_time*3)*3,Color(.3,.68,.6,.12))
	var content_top=float(db.assets[b.id].get("content_box",[0,0,512,476])[1])
	var shown_height=size.y*(476.0-content_top)/512.0
	health_bar(pos-Vector2(55,shown_height+15),110,b.hp/b.max_hp,b.side)
	if b.base:
		draw_string(font,pos-Vector2(74,shown_height+27),"我方纸城" if b.side==player_side else "敌方纸城",HORIZONTAL_ALIGNMENT_LEFT,-1,roundi(12/scale.x) if mobile_ui else 21,INK)

func health_bar(pos: Vector2, length: float, ratio: float, side: int):
	draw_rect(Rect2(pos,Vector2(length,8)),Color(.16,.14,.12,.65))
	draw_rect(Rect2(pos+Vector2(1,1),Vector2((length-2)*clampf(ratio,0,1),6)),Color("4c8a91") if side==player_side else Color("c45c43"))

func unit_height(id: String) -> float:
	var cache_scale: float=scale.y if mobile_ui else 1.0
	if absf(cache_scale-unit_height_cache_scale)>.0001:
		unit_height_cache.clear();unit_height_cache_scale=cache_scale
	if unit_height_cache.has(id):return float(unit_height_cache[id])
	var world_height: float=float(db.assets[id].get("world_height",1.4))
	var result: float=world_height*PX*PUPPET_SCALE
	if mobile_ui:
		var minimum: float=52.0 if db.balance.units[id].get("economy",false) else 60.0
		minimum*=maxf(1,world_height/1.42)
		result=maxf(result,minimum/maxf(.1,scale.y))
	unit_height_cache[id]=result
	return result

func draw_unit(u: Dictionary):
	if not sim.visible_to(player_side,u):return
	var pos=unit_position(u)
	if pos.x < -250 or pos.x>width+250: return
	var meta=db.assets[u.id]
	var hh: float=unit_height(u.id)
	var working: bool=u.anim=="mine"
	var unloading: bool=u.anim=="unload"
	var modulation=Color(1.4,1.3,1.2) if u.hurt>0 else Color.WHITE
	if u.clone: modulation=Color(.75,1,1,.7)
	if u.get("objective_unit",false) or not str(u.get("display_name","")).is_empty():draw_string(font,pos-Vector2(46,hh+20),u.get("display_name","目标"),HORIZONTAL_ALIGNMENT_LEFT,-1,19,Color("b74532"))
	paper_ellipse(pos+Vector2(0,4),Vector2(hh*.3,7+hh*.022),Color(0,0,0,.12))
	draw_frame_unit(u,pos,meta,modulation)
	if u.cargo>0:
		var cargo_pos=pos+Vector2(-float(u.facing)*hh*.29,-hh*.76)
		draw_circle(cargo_pos,10/scale.x if mobile_ui else 11,Color("b9964f"));draw_circle(cargo_pos,10/scale.x if mobile_ui else 11,INK,false,1)
		draw_string(font,cargo_pos+(Vector2(-4,4)/scale if mobile_ui else Vector2(-6,6)),str(u.cargo),HORIZONTAL_ALIGNMENT_LEFT,-1,roundi(11/scale.x) if mobile_ui else 15,PAPER)
	if working or unloading:
		var progress: float=clampf(float(u.job_time)/maxf(.01,float(u.get("work_duration",1))),0,1)
		draw_rect(Rect2(pos+Vector2(-24,12),Vector2(48,4)),Color(INK,.35))
		draw_rect(Rect2(pos+Vector2(-24,12),Vector2(48*progress,4)),Color("b9964f") if working else Color("31747c"))
	if u.anim=="queue" and selected_uid==u.uid:draw_string(font,pos+Vector2(-23,34),"待矿位",HORIZONTAL_ALIGNMENT_LEFT,-1,16,INK)
	# Ownership is independent of native faction art, including converted units.
	var side_color=Color("4c8a91") if u.side==player_side else Color("c45c43")
	var direction: float=1 if u.side==0 else -1
	draw_ownership(pos,direction,side_color)
	if db.balance.units[u.id].get("economy",false):
		var badge=pos+Vector2(-float(u.facing)*hh*.3,-hh*.82)
		draw_rect(Rect2(badge-(Vector2(9,9)/scale if mobile_ui else Vector2(14,12)),Vector2(18,18)/scale if mobile_ui else Vector2(28,23)),side_color)
		draw_string(font,badge+(Vector2(-6,4)/scale if mobile_ui else Vector2(-9,7)),"我" if u.side==player_side else "敌",HORIZONTAL_ALIGNMENT_LEFT,-1,roundi(12/scale.x) if mobile_ui else 17,Color("fff8e9"))
	if u.hp<u.max_hp or selected_uid==u.uid or selected_spell!="": health_bar(pos-Vector2(25,hh+6),50,u.hp/u.max_hp,u.side)
	if selected_uid==u.uid: draw_arc(pos+Vector2(0,4),hh*.35,0,TAU,32,Color("b9964f"),2,true)
	for key in u.statuses:
		var status_pos=pos-Vector2(0,hh*.48)
		match key:
			"protect": paper_ellipse(status_pos,Vector2(hh*.35,hh*.51),Color(.8,.63,.27,.13)); draw_arc(status_pos,hh*.46,-1.4,1.4,20,Color("b9964f"),3,true)
			"bind","root","stun":
				for n in range(3): draw_arc(status_pos+Vector2(0,float(n-1)*18),hh*.28,0,TAU,20,Color(.26,.4,.38,.7),2,true)
			"poison": draw_circle(pos-Vector2(0,hh*.85),9,Color("78617d")); draw_string(font,pos-Vector2(7,hh*.85-6),"墨",HORIZONTAL_ALIGNMENT_LEFT,-1,14,PAPER)
			"cold": paper_ellipse(status_pos,Vector2(hh*.34,hh*.48),Color(.27,.58,.66,.12))
			"exposed":
				draw_line(status_pos+Vector2(-18,-14),status_pos+Vector2(-7,-4),Color("c65c42"),3,true)
				draw_line(status_pos+Vector2(7,4),status_pos+Vector2(18,14),Color("c65c42"),3,true)
			"fury": draw_arc(status_pos,hh*.48,visual_time*3,visual_time*3+4,24,Color("b74532"),3,true)
			"silence":draw_string(font,pos-Vector2(12,hh+18),"禁",HORIZONTAL_ALIGNMENT_LEFT,-1,20,MANA)
			"burn":draw_arc(status_pos,hh*.39,visual_time*4,visual_time*4+4.8,24,Color("b9673f"),3,true)
			"haste":draw_line(pos+Vector2(-24,10),pos+Vector2(-6,10),MANA,3,true)
			"strength":draw_arc(status_pos,hh*.42,visual_time*2,visual_time*2+3.5,20,Color("aa8a32"),2,true)

func draw_ownership(pos: Vector2,direction: float,color: Color):
	if ownership_meshes.is_empty():
		# Preserve both native shapes, including their opposite inward notch.
		for sign_value in [1.0,-1.0]:
			var points=PackedVector2Array([Vector2(-15,5),Vector2(15,5),Vector2(15+sign_value*5,9),Vector2(15,12),Vector2(-15,12),Vector2(-15+sign_value*5,9)])
			var vertices=PackedVector3Array();var colors=PackedColorArray()
			for point in points:vertices.append(Vector3(point.x,point.y,0));colors.append(Color.WHITE)
			var arrays: Array=[];arrays.resize(Mesh.ARRAY_MAX)
			arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_COLOR]=colors;arrays[Mesh.ARRAY_INDEX]=Geometry2D.triangulate_polygon(points)
			var mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays);ownership_meshes.append(mesh)
	draw_mesh(ownership_meshes[0 if direction==1 else 1],null,Transform2D(0,pos),color)

func draw_frame_unit(u: Dictionary,pos: Vector2,meta: Dictionary,modulation: Color):
	var profile: Dictionary=db.unit_frames[u.id]
	var sample: Dictionary=hit_holds.get(u.uid,{}).get("pose",u) if u.anim!="death" else u
	var selected: Dictionary=FramePlayer.selection(sample,profile,float(db.unit_actions[u.id].get("recovery",.3)),float(db.balance.units[u.id].get("windup",.3)))
	var sf: float=unit_height(u.id)/float(profile.source_height)
	var anchor=Vector2(profile.anchor[0],profile.anchor[1])
	draw_set_transform(pos+canvas_shift,0,Vector2(float(u.facing)*sf,sf))
	var atlas_path: String=str(profile.atlas)
	var atlas: Texture2D=unit_atlas_cache.get(atlas_path)
	if atlas==null:
		atlas=db.texture(atlas_path);unit_atlas_cache[atlas_path]=atlas
	draw_texture_rect_region(atlas,Rect2(-anchor,Vector2(profile.frame_size[0],profile.frame_size[1])),FramePlayer.region(profile,selected.frame),modulation)
	draw_set_transform(canvas_shift)

func action_tip(u: Dictionary) -> Vector2:
	var meta: Dictionary=db.assets[u.id]
	var p: Dictionary=db.unit_frames[u.id]
	var sf: float=unit_height(u.id)/float(p.source_height)
	return unit_position(u)+Vector2((float(p.release_origin[0])-float(p.anchor[0]))*float(u.facing)*sf,(float(p.release_origin[1])-float(p.anchor[1]))*sf)

func draw_missile(pos: Vector2,direction: Vector2,style: String,color: Color,size_value: float=1):
	var d: Vector2=direction.normalized();var n=Vector2(-d.y,d.x)
	match style:
		"arrow","fire_arrow","bolt","spear","needle","frost":
			var length: float=58 if style=="spear" else 30 if style=="arrow" else 23 if style=="bolt" else 17
			var thickness: float=3.3 if style=="spear" else 2
			draw_line(pos-d*length*size_value,pos,color,thickness*size_value,true)
			draw_colored_polygon(PackedVector2Array([pos+d*8*size_value,pos-d*5*size_value+n*4*size_value,pos-d*5*size_value-n*4*size_value]),INK)
			if style in ["arrow","fire_arrow","bolt"]:
				for sign_value in [-1,1]:draw_line(pos-d*(length-4)*size_value,pos-d*length*size_value+n*5*sign_value*size_value,PAPER,2,true)
			if style=="fire_arrow":draw_circle(pos,4,Color("f29a42"));draw_line(pos-d*9,pos-d*18,Color("ba452a"),3,true)
			if style=="frost":draw_colored_polygon(PackedVector2Array([pos+d*10,pos-d*5+n*7,pos-d*15,pos-d*5-n*7]),Color("cde7e8"))
		"coin":
			draw_colored_polygon(PackedVector2Array([pos+d*10,pos+n*7,pos-d*10,pos-n*7]),Color("c2a354"));draw_line(pos-d*5,pos+d*5,INK,2,true)
		"glyph":
			draw_colored_polygon(PackedVector2Array([pos+d*10+n*4,pos+d*10-n*4,pos-d*14-n*4,pos-d*14+n*4]),PAPER);draw_line(pos-d*9,pos+d*6,Color("806990"),2,true)
		"page_breath":
			for i in range(3):
				var center: Vector2=pos-d*float(i)*12+n*float(i-1)*5
				draw_colored_polygon(PackedVector2Array([center+d*9,center+n*7,center-d*11,center-n*7]),Color("f9f2df"))
				draw_line(center-d*6,center+d*5,Color("8a7095"),1.5,true)
		"seed":draw_circle(pos,5,Color("607946"));draw_circle(pos-Vector2(1,1),2,Color("d4c69d"))
		"kite":
			draw_colored_polygon(PackedVector2Array([pos+d*11,pos+n*10,pos-d*12,pos-n*10]),Color("d5e4e6"));draw_line(pos-d*12,pos-d*27,Color("638198"),2,true)
		"snow":
			draw_circle(pos,7,Color("b5d1d7"))
			for i in range(6):draw_line(pos,pos+Vector2.from_angle(float(i)*TAU/6)*11,Color("f2faf1"),3,true)
		"fire_pot":
			draw_circle(pos,9,Color("a95f36"));draw_arc(pos,9,.4,2.7,12,INK,2,true);draw_line(pos+Vector2(0,-7),pos+Vector2(3,-16),Color("efac55"),3,true)
		"cannon","mortar":
			draw_circle(pos,8 if style=="cannon" else 10,INK);draw_circle(pos-Vector2(2,2),4,Color("baa889"))
		"fire":
			draw_colored_polygon(PackedVector2Array([pos+d*11,pos-d*17+n*7,pos-d*27,pos-d*15-n*7]),Color("c64b26"))
			draw_circle(pos,5,Color("f7d483"))
		"chain":
			for i in range(5):draw_arc(pos-d*i*8,4,0,TAU,9,Color("988275"),2,true)
			draw_colored_polygon(PackedVector2Array([pos+d*9,pos+n*9,pos-d*9,pos-n*9]),INK)
		"sound":draw_arc(pos,11,-1.1+d.angle(),1.1+d.angle(),15,color,3,true)
		"gear":
			draw_circle(pos,7,Color("ba924b"));draw_circle(pos,3,INK)
			for i in range(8):draw_line(pos+Vector2.from_angle(float(i)*TAU/8)*6,pos+Vector2.from_angle(float(i)*TAU/8)*10,Color("ba924b"),3,true)
		"leaf","fan","paper","seal":
			draw_colored_polygon(PackedVector2Array([pos+d*11,pos-d*6+n*8,pos-d*13,pos-d*6-n*8]),Color("7b9a5b") if style=="leaf" else PAPER)
			draw_line(pos-d*8,pos+d*6,color,2,true)
		_:
			draw_circle(pos,10,Color(color,.18));draw_circle(pos,5,color);draw_circle(pos-Vector2(1,2),2,PAPER)

func draw_projectile(p: Dictionary):
	if p.get("observed_only",false):
		if location_visible_cached(float(p.x),float(p.y)):
			var direction: Vector2=Vector2(1 if int(p.side)==0 else -1,0)
			draw_missile(point_to_screen(p.x,p.y)-Vector2(0,75),direction,p.style,Color("b9964f"))
		return
	if not location_visible_cached(float(p.x),float(p.y)):return
	var elapsed: float=float(p.total)-float(p.left)
	if elapsed<float(p.get("delay",0)):return
	var progress: float=clampf((elapsed-float(p.get("delay",0)))/maxf(.01,float(p.total)-float(p.get("delay",0))),0,1)
	var target: Dictionary=sim.actor(int(p.target))
	var start=point_to_screen(p.start_x,p.start_y)+Vector2(float(p.get("render_dx",0)),float(p.get("render_dy",-98)))
	var end=point_to_screen(p.end_x,p.end_y)-Vector2(0,75)
	if not target.is_empty() and sim.visible_to(player_side,target):
		end=(point_to_screen(target.x,target.y)-Vector2(0,120) if target.get("building",false) else unit_position(target)-Vector2(0,unit_height(target.id)*.55))
	var arc: float=94 if p.style in ["mortar","snow","fire_pot"] else 26 if p.style in ["spear","arrow","fire_arrow","cannon","kite","frost","coin"] else 8
	var pos=start.lerp(end,progress)-Vector2(0,sin(progress*PI)*arc)
	var tangent: Vector2=(end-start)-Vector2(0,cos(progress*PI)*PI*arc)
	var color=Color("b74532") if p.style=="fire" else Color("756089") if p.style in ["soul","ink"] else Color("b9964f")
	draw_missile(pos,tangent,p.style,color)
	if p.style in ["fire","soul","orb","ink","seal"]:
		for i in range(1,4):draw_circle(pos-tangent.normalized()*i*8,4-i,Color(color,.22))
	if p.reflected:draw_arc(pos,13,0,TAU,16,Color("377b78"),2,true)

func draw_effect(e: Dictionary):
	if not location_visible_cached(float(e.x),float(e.y)):return
	var t=1-e.life/e.total
	var a=clampf((1-t)*1.4,0,1)
	var pos=point_to_screen(e.x,e.y)-Vector2(0,90)
	var color=tint(e.color,a)
	var data=e.data
	match e.type:
		"unit_special":
			var actor: Dictionary=sim.actor(int(data.get("uid",0)));var receiver: Dictionary=sim.actor(int(data.get("target_uid",0)))
			if actor.is_empty():return
			var start: Vector2=action_tip(actor)
			var end: Vector2=(point_to_screen(receiver.x,receiver.y) if receiver.get("building",false) else unit_position(receiver))-Vector2(0,64) if not receiver.is_empty() else start+Vector2(32,-12)
			for i in range(4):
				var q: Vector2=start.lerp(end,clampf(t+float(i)*.13,0,1))+Vector2(0,-sin(t*PI)*12)
				draw_circle(q,3.5,tint(MANA,a));draw_line(q+Vector2(-4,0),q+Vector2(4,0),tint(PAPER,a),1,true)
		"weapon_release":
			var actor: Dictionary=sim.actor(int(data.uid));var g: String=data.gesture
			if data.ranged:
				if actor.is_empty():return
				pos=action_tip(actor)
				if g in ["mortar","crossbow","ballista","stamp_machine","kite_launcher","bellows"]:
					var dir: float=data.facing
					for i in range(4):
						var ray=Vector2(dir,0).rotated((i-1.5)*.23)
						draw_line(pos+ray*3,pos+ray*(12+t*18),tint(PAPER,a),3*(1-t),true)
					if g in ["mortar","bellows"]:draw_circle(pos+Vector2(dir*t*16,-t*5),5+t*16,Color("84756c",a*.20))
				elif g=="bow":draw_arc(pos,10+t*8,-.65, .65,10,tint(PAPER,a*.6),1,true)
				elif g=="throw":draw_line(pos-Vector2(data.facing*15,0),pos+Vector2(data.facing*6,0),tint(PAPER,a),2,true)
				else:
					for i in range(4):
						var q=pos+Vector2.from_angle(i*TAU/4+t*2)*(7+t*20)
						draw_circle(q,3*(1-t),color)
			else:
				var victim: Dictionary=sim.actor(int(data.get("target_uid",0)))
				if victim.is_empty() and not data.has_all(["target_x","target_y"]):return
				pos=(point_to_screen(data.target_x,data.target_y) if victim.is_empty() or victim.get("building",false) else unit_position(victim))-Vector2(0,58)
				if g in ["hammer","punch","ram","bomb","root_bash","shield","frame_guard"]:
					paper_ellipse(pos+Vector2(0,51),Vector2(12+t*36,3+t*5),tint(color,a*.3))
					for i in range(4):draw_line(pos,pos+Vector2.from_angle(float(i)*TAU/4)* (10+t*20),tint(PAPER,a),3,true)
				elif g in ["fence","stab","ambush","lance","pike","shield_thrust","staff_push","hook"]:
					draw_line(pos-Vector2(data.facing*(16+t*10),0),pos+Vector2(data.facing*15,0),tint(PAPER,a),4*(1-t),true)
				else:
					draw_arc(pos,18+t*16,-1.3 if data.facing>0 else 1.8,1.3 if data.facing>0 else 4.5,18,tint(PAPER,a),5*(1-t),true)
					draw_arc(pos,24+t*16,-1.3 if data.facing>0 else 1.8,1.3 if data.facing>0 else 4.5,18,color,2*(1-t),true)
		"mine_strike":
			var worker: Dictionary=sim.actor(int(data.uid))
			if worker.is_empty() or worker.anim not in ["mine","load","walk"]:return
			pos=unit_position(worker)+Vector2(float(data.facing)*47,-27)
			for n in range(5):
				var direction=Vector2((float(n)-2)*.36,-1.0).normalized()
				var chip=pos+direction*(8+t*29)+Vector2(0,t*t*26)
				draw_colored_polygon(PackedVector2Array([chip+Vector2(-4,-2),chip+Vector2(3,-4),chip+Vector2(5,2),chip+Vector2(-2,4)]),tint(Color("d7ac48") if n%2 else PAPER,a))
			if t<.25:draw_line(pos-Vector2(9,0),pos+Vector2(9,0),tint(PAPER,a),3,true)
		"cargo_loaded":
			var worker: Dictionary=sim.actor(int(data.uid))
			if worker.is_empty():return
			pos=unit_position(worker)-Vector2(0,70)
			for n in range(3):draw_circle(pos+Vector2((n-1)*12,-t*24),4,tint(Color("bc913c"),a))
		"muzzle":
			var direction: float = 1 if int(data.get("side",0))==0 else -1
			var flash=pos+Vector2(direction*35,-8)
			for n in range(3):
				var ray=Vector2(direction,0).rotated((n-1)*.34)
				draw_line(flash+ray*6,flash+ray*(18+t*15),tint(PAPER,a),5*(1-t),true)
				draw_line(flash+ray*6,flash+ray*(18+t*15),color,2*(1-t),true)
		"slash":
			var victim: Dictionary=sim.actor(int(data.get("target_uid",0)))
			if not victim.is_empty():pos=unit_position(victim)-Vector2(0,58)
			elif data.has_all(["target_x","target_y"]):pos=point_to_screen(data.target_x,data.target_y)-Vector2(0,58)
			else:return
			var direction: float=float(data.get("facing",1))
			draw_arc(pos,22+float(t)*12,-1.1 if direction>0 else 2,1.1 if direction>0 else 4.2,15,tint(PAPER,a),6,true)
			draw_arc(pos,26+float(t)*12,-1.1 if direction>0 else 2,1.1 if direction>0 else 4.2,15,color,2,true)
		"hit":
			var victim: Dictionary=sim.actor(int(data.uid))
			if not victim.is_empty() and not victim.get("building",false):pos=unit_position(victim)-Vector2(0,56)
			else:pos.x+=float(data.get("visual_dx",0))
			for n in range(5):
				var angle=float(n)/5*TAU
				draw_line(pos+Vector2(cos(angle),sin(angle))*8,pos+Vector2(cos(angle),sin(angle))*(20+t*30),tint(PAPER,a),3)
		"death":
			if data.has("puppet") and db.unit_frames.has(data.id):
				var fallen: Dictionary=data.puppet.duplicate(true);fallen.anim="death";fallen.anim_t=t*.85;fallen.hurt=0
				draw_frame_unit(fallen,point_to_screen(e.x,e.y),db.assets[data.id],Color(1,1,1,1-smoothstep(.80,1,t)))

		"bone_burst":
			for i in range(9):
				var offset=Vector2.from_angle(float(i)*TAU/9)*(10+t*58)
				draw_line(pos+offset-Vector2(3,0),pos+offset+Vector2(3,0),tint(PAPER,a),3,true)
				paper_ellipse(pos+offset,Vector2(4,2),tint(Color("75667b"),a))
		"dash":
			draw_line(point_to_screen(float(data.get("from",e.x)),float(data.get("from_y",e.y)))-Vector2(0,75),pos,color,8*(1-t))
		"stamp":
			pos=point_to_screen(e.x,e.y)-Vector2(0,45+(1-t)*160)
			draw_rect(Rect2(pos-Vector2(74,60),Vector2(148,90)),tint(Color("b74532"),a))
			draw_rect(Rect2(pos-Vector2(64,51),Vector2(128,73)),tint(PAPER,a),false,4)
			draw_string(font,pos+Vector2(-25,2),"印",HORIZONTAL_ALIGNMENT_LEFT,-1,48,tint(PAPER,a))
		"lightning":
			var vertices=PackedVector2Array([pos+Vector2(-24,-220),pos+Vector2(17,-126),pos+Vector2(-9,-129),pos+Vector2(23,-25),pos+Vector2(-7,-29),pos+Vector2(0,28)])
			draw_polyline(vertices,tint(PAPER,a),11,true); draw_polyline(vertices,tint(MANA,a),5,true)
		_:
			var aliases={"repair":"repair","cold":"cold","fury":"impact","sacrifice":"sacrifice","bind":"control","poison":"poison","convert":"control","burst":"impact","protect":"protect","clone":"clone","fire":"fire","root":"root","guardian":"summon","summon":"summon","blast":"impact","muzzle":"fire"}
			var id="fx."+aliases.get(e.type,"impact")
			var tex=db.art(id)
			if tex:
				var size=140.0+float(data.get("radius",0))*35
				draw_texture_rect(tex,Rect2(pos-Vector2(size,size)*.5,Vector2(size,size)),false,Color(1,1,1,a))
			if e.type in ["fire","burst","blast","summon"]:
				draw_arc(point_to_screen(e.x,e.y),20+t*95,0,TAU,24,color,4*(1-t),true)

func target_at(screen: Vector2) -> int:
	if sim==null: return 0
	var best=0; var closest=100000.0;var legal_best=0;var legal_closest=100000.0
	var single=selected_spell!="" and selected_spell.get_slice(".",2) in ["repair","fury","sacrifice","protect","clone","lightning","bind","convert","root"]
	for u in sim.units:
		if not sim.visible_to(player_side,u):continue
		var hh: float=unit_height(u.id)
		var pos=unit_position(u)-Vector2(0,hh*.5)
		var distance=screen.distance_to(pos)
		if absf(screen.x-pos.x)<maxf(24/scale.x if mobile_ui else 32,hh*.34) and absf(screen.y-pos.y)<maxf(24/scale.y if mobile_ui else 0,hh*.56):
			if distance<closest:best=u.uid;closest=distance
			if single and distance<legal_closest and sim.spell_error(player_side,selected_spell,u.x,u.uid)=="":legal_best=u.uid;legal_closest=distance
	return legal_best if legal_best>0 else best

func draw_target_preview():
	if selected_spell=="" or sim==null: return
	if mobile_ui and not mobile_pointer_active:return
	var def=db.balance.spells[selected_spell]
	var single=selected_spell.get_slice(".",2) in ["repair","fury","sacrifice","protect","clone","lightning","bind","convert","root"]
	var target: int = target_at(pointer)
	var x: float = screen_to_world(pointer.x)
	var y: float = (pointer.y-floor_y())/PY
	var a: Dictionary = sim.actor(target)
	if not a.is_empty():
		var body: Vector2=render_physical_point(a);x=body.x;y=body.y
	var error=sim.spell_error(player_side,selected_spell,x,target,y)
	var color=Color("377b78") if error=="" else Color("b74532")
	if single:
		if target>0:
			var u=sim.actor(target)
			var hh: float=unit_height(u.id)
			draw_arc(unit_position(u)-Vector2(0,hh*.55),hh*.57,0,TAU,32,color,2,true)
		else:draw_circle(pointer,9,color,false,2,true)
		return
	var area_radius: float=float(def.get("zone",{}).get("radius",def.get("radius",.6)))
	var r=area_radius*PX
	var pos=point_to_screen(x,y)
	var ry: float = area_radius*PY
	paper_ellipse(pos,Vector2(r,ry),tint(color,.13))
	var vertices=PackedVector2Array()
	for i in range(40):
		var angle=float(i)/39*TAU
		vertices.append(pos+Vector2(cos(angle)*r,sin(angle)*ry))
	draw_polyline(vertices,color,2,true)

func unit_position(u: Dictionary) -> Vector2:
	var body: Vector2=render_physical_point(u)
	var pos=world_to_screen(body.x,float(int(u.uid)%5)*4-8,body.y)
	return pos

func render_physical_point(u: Dictionary) -> Vector2:
	var uid: int=int(u.get("uid",0))
	if render_point_refs.has(uid) and is_same(render_point_refs[uid],u):return render_point_cache[uid]
	var body: Vector2=sim.physical_point(u)
	render_point_refs[uid]=u;render_point_cache[uid]=body
	return body

func minimap_rect() -> Rect2:
	return mobile_minimap if mobile_ui else desktop_minimap if desktop_minimap.has_area() else Rect2(544,height-148,496,30)

func minimap_point(x: float,y: float) -> Vector2:
	var box=minimap_rect()
	return Vector2(box.position.x+x/sim.map.length*box.size.x,box.position.y+(y-sim.map.bounds.position.y)/sim.map.bounds.size.y*box.size.y)

func draw_minimap(target):
	var box=minimap_rect()
	if not box.has_area():return
	target.draw_rect(box,Color(UITheme.CARD,.96))
	target.draw_rect(box,Color(UITheme.EDGE,.9),false,1.0)
	for edge_id in sim.map.edges:
		var points=PackedVector2Array()
		for p in sim.map.edges[edge_id].points:points.append(minimap_point(p.x,p.y))
		target.draw_polyline(points,Color(UITheme.EDGE,.85),2,true)
		if sim.config.get("fog",true):
			var length: float=sim.map.edges[edge_id].length
			var distance: float=0
			while distance<length:
				var finish: float=minf(length,distance+.18)
				var anchor: Dictionary=sim.map.anchor(edge_id,(distance+finish)*.5)
				if not sim.visibility.point_visible(player_side,anchor):
					var start: Vector2=sim.map.point(edge_id,distance);var end: Vector2=sim.map.point(edge_id,finish)
					var explored: bool=sim.visibility.point_explored(player_side,anchor)
					target.draw_line(minimap_point(start.x,start.y),minimap_point(end.x,end.y),Color(UITheme.MIDNIGHT,.38 if explored else .86),7,true)
				distance=finish
	for b in sim.bases+sim.buildings:
		if not sim.visible_to(player_side,b):continue
		var pos=minimap_point(b.x,b.y)
		target.draw_rect(Rect2(pos-Vector2(4,5),Vector2(8,10)),UITheme.JADE if b.side==player_side else UITheme.SEAL)
	# Hollow signs are stale building intelligence, never hidden live state.
	for remembered in sim.visibility.last_seen[player_side].values():
		if sim.visibility.point_visible(player_side,remembered):continue
		var pos=minimap_point(remembered.x,remembered.y)
		target.draw_rect(Rect2(pos-Vector2(4,5),Vector2(8,10)),UITheme.LIGHT_MUTED,false,1)
	for mine in sim.map.definition.mines:
		if int(mine.owner)==player_side or sim.visibility.point_visible(player_side,mine):target.draw_circle(minimap_point(mine.x,mine.y),3,UITheme.GOLD)
		elif sim.visibility.point_explored(player_side,mine):target.draw_circle(minimap_point(mine.x,mine.y),3,UITheme.LIGHT_MUTED,false,1,true)
	if sim.config.get("win","") in ["escort","intercept"]:
		var goal: Dictionary = sim.config.get("objective_anchor",sim.map.definition.objective_anchor)
		var pos=minimap_point(goal.x,goal.y)
		target.draw_line(pos+Vector2(0,-9),pos+Vector2(0,9),UITheme.SEAL,3,true)
	for u in sim.units:
		if not sim.visible_to(player_side,u):continue
		var pos=minimap_point(u.x,u.y)
		target.draw_circle(pos,2 if db.balance.units[u.id].get("economy",false) else 3,UITheme.JADE if u.side==player_side else UITheme.SEAL)
		if u.get("objective_unit",false):target.draw_circle(pos,6,UITheme.INK,false,2,true)
	var visible_width=width/PX
	if not economy_warning.is_empty():
		var warning_point: Vector2=minimap_point(float(economy_warning.x),float(economy_warning.y))
		# Stage zoom must not shrink an important HUD signal along with paper actors.
		var warning_scale: float=1.0/maxf(.1,scale.x)
		var margin: Vector2=Vector2.ONE*10.0*warning_scale
		warning_point=warning_point.clamp(box.position+margin,box.end-margin)
		var warning_radius: float=(9.0 if reduced_motion else 9.0+sin(visual_time*5.0))*warning_scale
		target.draw_circle(warning_point,warning_radius,Color("b74532",.16))
		target.draw_circle(warning_point,warning_radius,Color("b74532"),false,2*warning_scale,true)
		target.draw_line(warning_point-Vector2(0,3)*warning_scale,warning_point+Vector2(0,1)*warning_scale,Color("b74532"),2*warning_scale,true)
		target.draw_circle(warning_point+Vector2(0,4)*warning_scale,1.2*warning_scale,Color("b74532"))
	var left=box.position.x+(camera_x-visible_width*.5)/sim.map.length*box.size.x
	target.draw_rect(Rect2(left,box.position.y-2,visible_width/sim.map.length*box.size.x,box.size.y+4),UITheme.GOLD,false,2)

func draw_spell_zone(zone: Dictionary):
	if not location_visible_cached(zone.x,zone.y):return
	var center: Vector2=point_to_screen(zone.x,zone.y)
	var hue: Color=Color("756089")
	match str(zone.status):
		"burn":hue=Color("c55532")
		"cold":hue=Color("4e899c")
		"silence":hue=Color("878478")
	if float(zone.get("heal",0))>0:hue=Color("58845b")
	if float(zone.get("vision",0))>0:hue=Color("bc9349")
	var radius: float=maxf(.3,float(zone.radius))
	var opacity: float=minf(1.0,zone.left)*.22
	var mist=PackedVector2Array()
	for i in range(32):mist.append(center+Vector2(cos(i*TAU/32)*radius*PX,-20+sin(i*TAU/32)*38))
	draw_colored_polygon(mist,Color(hue,opacity))
	for i in range(5):
		var phase: float=visual_time*1.8+i*TAU/5
		var p: Vector2=center+Vector2(cos(phase)*radius*PX*.7,-24+sin(phase)*12)
		draw_line(p,p+Vector2(4,-14-sin(phase)*5),Color(hue,.55),2,true)
	if float(zone.get("vision",0))>0:
		draw_line(center,center-Vector2(0,72),hue,3,true)
		draw_circle(center-Vector2(0,72),9,Color(hue,.75))
		draw_arc(center-Vector2(0,72),16,visual_time,visual_time+PI,12,hue,2,true)
	elif float(zone.get("speed",0))>0:
		var forward: float=1 if int(zone.side)==0 else -1
		draw_line(center-Vector2(10*forward,16),center+Vector2(20*forward,-16),hue,3,true)
