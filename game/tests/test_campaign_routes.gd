extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Progress=preload("res://scripts/campaign_progress.gd")
var checks: int=0
var failures: Array=[]
func _initialize():call_deferred("run")
func verify(value: bool,note: String):
	checks+=1
	if not value and failures.size()<20:failures.append(note)
func fresh(p) -> Dictionary:
	var profile: Dictionary={"schema":3,"stars":{},"story_flags":{}}
	p.migrate(profile,profile.duplicate(true));return profile
func run():
	var db=Data.new();var p=Progress.new(db)
	var narrative: Dictionary=db.read_json("res://data/campaign-narrative.json").profiles
	verify(p.nodes.size()==200,"all current campaign IDs represented")
	var reachable: Dictionary={}
	for level in db.campaign:
		var node: Dictionary=p.nodes[level.id]
		verify(int(node.index)==int(level.index),"stable index "+level.id)
		for parent in node.get("unlock_all",[])+node.unlock_any:
			verify(p.levels.has(parent),"known parent "+level.id)
			verify(int(p.nodes[parent].index)<int(level.index),"acyclic dependency "+level.id)
			verify(p.nodes[parent].successors.has(level.id),"graph reverse link "+level.id)
		verify(p.available({"campaign_completed":reachable},level.id),"reachable without skipped chapter "+level.id)
		reachable[level.id]=true
		verify(not level.story_before.is_empty() and not level.story_after.is_empty(),"every single-player map has before/after story "+level.id)
		if narrative.has(level.id):
			var beat: Dictionary=narrative[level.id]
			verify(beat.map==level.map and beat.objective==level.win,"authored story bound to real objective "+level.id)
			verify(beat.evidence_flag==level.story_flag,"stable evidence flag "+level.id)
			var edges: Array=db.maps[level.map].edges.map(func(edge):return edge.id)
			verify(beat.roads==edges,"story geographic references exist "+level.id)
			verify(not str(beat.goal).is_empty() and not str(beat.geography_reason).is_empty(),"story and spatial motivation "+level.id)
		else:verify(false,"missing map-specific narrative "+level.id)
	verify(narrative.size()==200,"all200 maps have distinct authored profiles")
	# Enumerate all64 combinations of six narrative alternatives. Each must
	# reach chapter2 without falsely completing the six unvisited companions.
	for mask in range(64):
		var profile: Dictionary=fresh(p)
		var route: Array=[1,2+(mask&1),4,5+((mask>>1)&1),7,8+((mask>>2)&1),10,11+((mask>>3)&1),13,14+((mask>>4)&1),16,17,18+((mask>>5)&1),20]
		for number in route:
			var id: String=db.campaign[number-1].id
			verify(p.record_victory(profile,id,2),"legal alternative "+str(mask)+"/"+id)
			verify(p.completed(profile,id),"selected page really completed")
			var saved: Dictionary=JSON.parse_string(JSON.stringify(profile))
			profile={"stars":saved.stars,"story_flags":saved.story_flags}
			p.migrate(profile,saved)
			verify(profile.campaign_completed==saved.campaign_completed,"roundtrip preserves actual pages")
			verify(profile.stars==saved.stars and profile.story_flags==saved.story_flags,"roundtrip preserves stars/evidence")
		verify(profile.campaign_completed.size()==14,"no phantom completion for optional routes")
		verify(p.available(profile,db.campaign[20].id),"chapter2 opens after chapter1 convergence")
		verify(p.recommended(profile).id==db.campaign[20].id,"continue advances to newly opened chapter")
		for pair in [[2,3],[5,6],[8,9],[11,12],[14,15],[18,19]]:
			var a: bool=p.completed(profile,db.campaign[pair[0]-1].id)
			var b: bool=p.completed(profile,db.campaign[pair[1]-1].id)
			verify(a!=b,"one actual evidence branch, not both")
			verify(p.available(profile,db.campaign[(pair[1] if a else pair[0])-1].id),"unvisited companion remains visitable")
		p.record_victory(profile,db.campaign[0].id,1)
		verify(int(profile.stars[db.campaign[0].id])==2,"replay does not reduce stars")
		verify(p.recommended(profile).id==db.campaign[20].id,"old replay does not roll chapter recommendation back")
	for old_frontier in range(200):
		var profile: Dictionary={"stars":{},"story_flags":{}}
		p.migrate(profile,{"schema":2,"unlocked":old_frontier,"stars":{},"story_flags":{}})
		verify(profile.campaign_completed.size()==old_frontier,"legacy genuinely linear history retained")
		verify(p.available(profile,db.campaign[old_frontier].id),"legacy current page remains accessible")
	var profile: Dictionary=fresh(p);var before: Dictionary=profile.duplicate(true)
	verify(not p.record_victory(profile,db.campaign[19].id,3) and profile==before,"locked finale cannot create story progress")
	verify(not p.record_victory(profile,"unknown",3) and profile==before,"unknown ID cannot create progress")
	verify(p.record_victory(profile,db.campaign[0].id,3),"first page is playable")
	verify(p.next_choices(profile,db.campaign[0].id).size()==2,"first actual victory opens two choices")
	p.record_victory(profile,db.campaign[1].id,1)
	verify(p.recommended(profile).id==db.campaign[3].id,"economic branch converges without guarding optional page")
	verify(not p.completed(profile,db.campaign[2].id) and not profile.story_flags.has(db.campaign[2].story_flag),"unvisited defense branch has no fabricated evidence")
	profile.campaign_completed=reachable.duplicate(true)
	verify(p.recommended(profile).id==p.finale,"complete ending remains replayable")
	var legacy: Dictionary={};p.migrate(legacy,{"schema":1,"unlocked":14})
	verify(legacy.campaign_completed.is_empty(),"old15-page unrelated campaign is not reinterpreted")
	# Exercise every authored local route and every order of compulsory
	# parallel investigations. Earlier chapters are explicit completed fixtures;
	# no route is credited for unvisited companion pages.
	var route_count: int=0
	for chapter in db.read_json("res://data/campaign-flow.json").chapters:
		for route in chapter.minimal_routes:
			route_count+=1
			var state: Dictionary=fresh(p)
			for i in range(int(chapter.index)*20):
				state.campaign_completed[db.campaign[i].id]=true
				state.story_flags[db.campaign[i].story_flag]=true
			var actual: Dictionary={}
			for id in route:
				verify(p.available(state,id),"local route action available "+id)
				verify(p.record_victory(state,id,2),"local route actual result accepted "+id)
				actual[id]=true
				verify(state.campaign_completed.size()==int(chapter.index)*20+actual.size(),"only real victories recorded")
				verify(state.story_flags.size()==int(chapter.index)*20+actual.size(),"only real evidence recorded")
				for choice in p.next_choices(state,id):verify(p.available(state,choice.id) and not p.completed(state,choice.id),"result suggests a playable incomplete page")
				var rec: Dictionary=p.recommended(state)
				verify(p.available(state,rec.id),"continue never dead-ends after parallel evidence")
				var saved: Dictionary=JSON.parse_string(JSON.stringify(state))
				var restored: Dictionary={"stars":saved.stars,"story_flags":saved.story_flags}
				p.migrate(restored,saved)
				verify(restored.campaign_completed==state.campaign_completed and restored.story_flags==state.story_flags,"all chapter save roundtrip")
				state=restored
			verify(actual.size()==int(chapter.minimum_actual_clears),"minimal route requires specified actual clears")
			for i in range(int(chapter.index)*20,int(chapter.index)*20+20):
				var item: Dictionary=db.campaign[i]
				verify(p.completed(state,item.id)==actual.has(item.id),"optional page not falsely cleared "+item.id)
				verify(state.story_flags.has(item.story_flag)==actual.has(item.id),"optional clue not invented "+item.id)
				if not actual.has(item.id):verify(p.available(state,item.id),"skipped optional page remains revisitable "+item.id)
			if int(chapter.index)<9:verify(p.available(state,db.campaign[(int(chapter.index)+1)*20].id),"chapter ending opens next chapter")
			else:verify(p.completed(state,p.finale),"all mandatory final evidence leads to ending")
	# Independent conjunction examples, not derived from the layer generator.
	var paired: Dictionary={"schema":3,"campaign_completed":{},"stars":{},"story_flags":{}}
	for i in range(20):paired.campaign_completed[db.campaign[i].id]=true
	p.record_victory(paired,"campaign.mo.01",2);p.record_victory(paired,"campaign.mo.02",2)
	verify(not p.available(paired,"campaign.mo.04"),"live wage alone cannot replace burial evidence")
	verify(p.recommended(paired).id=="campaign.mo.03","continue offers missing burial investigation")
	var pending: Dictionary=paired.duplicate(true)
	verify(not p.record_victory(paired,"campaign.mo.04",3) and paired==pending,"locked conjunction cannot grant stars or clue")
	p.record_victory(paired,"campaign.mo.03",2)
	verify(p.available(paired,"campaign.mo.04"),"both real investigations unlock shared hearing")
	verify(p.requirement_hint("campaign.mo.04")=="需完成02和03折","AND prerequisite communicates both pages")
	verify(p.requirement_hint("campaign.yin.04")=="需完成02或03折","OR prerequisite communicates alternatives")
	verify(p.requirement_hint("campaign.mo.01")=="需完成第1章20折","cross chapter prerequisite is unambiguous")
	print("CAMPAIGN_ROUTES: ",checks," checks; failures=",failures)
	var args=OS.get_cmdline_user_args()
	if args.has("--output"):FileAccess.open(args[args.find("--output")+1],FileAccess.WRITE).store_string(JSON.stringify({"checks":checks,"failures":failures,"opening_paths":64,"local_route_orders":route_count,"source_sha256":FileAccess.get_sha256("res://scripts/campaign_progress.gd"),"flow_sha256":FileAccess.get_sha256("res://data/campaign-flow.json"),"narrative_sha256":FileAccess.get_sha256("res://data/campaign-narrative.json"),"scope":"All200 map stories and graph dependencies; every authored local minimal route and mandatory parallel order, actual-clear conjunctions, no invented evidence, save roundtrips and200 legacy frontiers. Fixtures, not normal battle wins or human story review."},"  "))
	quit(0 if failures.is_empty() else 1)
