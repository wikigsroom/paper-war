extends RefCounted
# Story progression has its own graph; battlefield roads use MapRuntime.
var db
var nodes: Dictionary={}
var levels: Dictionary={}
var finale: String=""
func _init(data):
	db=data
	var flow: Dictionary=db.read_json("res://data/campaign-flow.json")
	nodes=flow.nodes;finale=flow.finale
	for level in db.campaign:levels[level.id]=level
func completed(profile: Dictionary,id: String) -> bool:
	return levels.has(id) and bool(profile.get("campaign_completed",{}).get(id,false))
func available(profile: Dictionary,id: String) -> bool:
	if not nodes.has(id):return false
	if completed(profile,id):return true
	for parent in nodes[id].get("unlock_all",[]):
		if not completed(profile,parent):return false
	var parents: Array=nodes[id].get("unlock_any",[])
	if parents.is_empty():return true
	for parent in parents:
		if completed(profile,parent):return true
	return false
func migrate(profile: Dictionary,saved: Dictionary):
	var done: Dictionary={}
	if int(saved.get("schema",1))>=3:
		for id in saved.get("campaign_completed",{}):
			if levels.has(id) and bool(saved.campaign_completed[id]):done[id]=true
	elif int(saved.get("schema",1))==2:
		# Schema2 really required every earlier mission; retain that history.
		var old_frontier: int=clampi(int(saved.get("unlocked",0)),0,db.campaign.size()-1)
		for i in range(old_frontier):done[db.campaign[i].id]=true
		for level in db.campaign:
			if int(saved.get("stars",{}).get(level.id,0))>0:done[level.id]=true
	profile["campaign_completed"]=done
	var last: String=str(saved.get("campaign_last_completed",""))
	profile["campaign_last_completed"]=last if completed(profile,last) else ""
	profile.schema=3
	sync_recommendation(profile)
func next_choices(profile: Dictionary,from_id: String) -> Array:
	var choices: Array=[]
	if not nodes.has(from_id):return choices
	for id in nodes[from_id].successors:
		if completed(profile,id):continue
		if available(profile,id):
			if not choices.has(levels[id]):choices.append(levels[id])
		else:
			# A conjunction needs the remaining actual pages, not a fictitious
			# clear of its siblings. Offer playable companions from this same
			# convergence so Continue cannot dead-end after the first evidence.
			for parent in nodes[id].get("unlock_all",[]):
				if available(profile,parent) and not completed(profile,parent) and not choices.has(levels[parent]):choices.append(levels[parent])
	return choices
func recommended(profile: Dictionary) -> Dictionary:
	var latest_chapter: int=0
	for index in range(0,db.campaign.size(),20):
		if available(profile,db.campaign[index].id):latest_chapter=index/20
	var choices: Array=next_choices(profile,str(profile.get("campaign_last_completed","")))
	for choice in choices:
		if int(choice.index)/20==latest_chapter:return choice
	# Once the ending is reached, continue points to its replay. Optional pages
	# remain accessible in the chapter map without resetting the story ending.
	if completed(profile,finale):return levels[finale]
	for level in db.campaign:
		if int(level.index)/20==latest_chapter and available(profile,level.id) and not completed(profile,level.id):return level
	return db.campaign[0]
func sync_recommendation(profile: Dictionary):
	profile.unlocked=int(recommended(profile).index)
func record_victory(profile: Dictionary,id: String,stars: int) -> bool:
	if not available(profile,id):return false
	if not profile.has("campaign_completed"):profile["campaign_completed"]={}
	profile.campaign_completed[id]=true
	if not profile.has("stars"):profile["stars"]={}
	if not profile.has("story_flags"):profile["story_flags"]={}
	profile.stars[id]=maxi(int(profile.stars.get(id,0)),clampi(stars,1,3))
	profile.story_flags[levels[id].get("story_flag",id)]=true
	profile["campaign_last_completed"]=id;profile.schema=3
	sync_recommendation(profile)
	return true
func requirement_hint(id: String) -> String:
	if not nodes.has(id):return "未知关卡"
	var required: PackedStringArray=[]
	var alternatives: PackedStringArray=[]
	for parent in nodes[id].get("unlock_all",[]):required.append(page_name(parent,id))
	for parent in nodes[id].get("unlock_any",[]):alternatives.append(page_name(parent,id))
	if required.is_empty() and alternatives.is_empty():return "起点"
	var terms: PackedStringArray=[]
	if not required.is_empty():terms.append("和".join(required))
	if not alternatives.is_empty():terms.append("或".join(alternatives))
	return "需完成"+"及".join(terms)+"折"
func page_name(parent: String,child: String) -> String:
	var number: String="%02d"%(int(nodes[parent].index)%20+1)
	return number if int(nodes[parent].chapter)==int(nodes[child].chapter) else "第%d章%s"%[int(nodes[parent].chapter)+1,number]
func status(profile: Dictionary,id: String) -> String:
	if completed(profile,id):return "已留证 · 可重访"
	return "可行动" if available(profile,id) else requirement_hint(id)
