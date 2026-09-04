/*
 * aris2puml — ARIS report script: EPC model → intermediate JSON (version 1).
 *
 * UNTESTED TEMPLATE. Written against the documented ARIS Script API
 * (ArisData, Model.ObjOccList, ObjOcc.OutEdges, Constants.OT_*) without an
 * ARIS installation to run it on. Expect to adjust the object-type
 * constants and the attribute lookups to your ARIS version and method
 * filter before first use. The JSON shape it writes is the contract in
 * aris2puml/readers/json_.py; keep that stable and everything downstream
 * works.
 *
 * Usage (ARIS Architect): select one or more EPC models, run the report,
 * save the returned text as <model>.json, then:  aris2puml <model>.json
 */

var KIND = {};
KIND[Constants.OT_FUNC] = "function";
KIND[Constants.OT_EVT] = "event";
KIND[Constants.OT_RULE] = "connector";           // XOR / AND / OR — refined below
KIND[Constants.OT_ORG_UNIT] = "lane";
KIND[Constants.OT_POS] = "lane";
KIND[Constants.OT_PERS_TYPE] = "lane";           // role
KIND[Constants.OT_FUNC] = "function";

// Process interface: a function occurrence whose symbol is the interface symbol.
var INTERFACE_SYMBOL = Constants.ST_PRCS_IF;

function connectorKind(occ) {
  var sym = occ.SymbolNum();
  if (sym == Constants.ST_OPR_XOR_1 || sym == Constants.ST_OPR_XOR_2) return "xor";
  if (sym == Constants.ST_OPR_AND_1 || sym == Constants.ST_OPR_AND_2) return "and";
  if (sym == Constants.ST_OPR_OR_1 || sym == Constants.ST_OPR_OR_2) return "or";
  return "xor";
}

function attr(item, attrNum) {
  var a = item.Attribute(attrNum, Context.getSelectedLanguage());
  return a.IsMaximized() ? a.getValue() : "";
}

function exportModel(model) {
  var lanes = [], laneIds = {}, nodes = [], edges = [], laneOf = {};
  var occs = model.ObjOccList();

  // pass 1: lanes (org units attached to functions) and control-flow nodes
  for (var i = 0; i < occs.length; i++) {
    var occ = occs[i], def = occ.ObjDef(), type = def.TypeNum();
    var kind = KIND[type];
    if (kind === "lane") {
      var lid = def.GUID();
      if (!laneIds[lid]) { laneIds[lid] = true; lanes.push({ id: lid, name: def.Name(-1) }); }
      continue;
    }
    if (!kind) continue;                          // info objects, systems, documents: dropped
    if (kind === "connector") kind = connectorKind(occ);
    var node = { id: occ.ObjOccGUID ? occ.ObjOccGUID() : def.GUID(), kind: kind };
    if (kind !== "xor" && kind !== "and" && kind !== "or") node.name = def.Name(-1);
    if (kind === "function" && occ.SymbolNum() == INTERFACE_SYMBOL) {
      node.kind = "interface";
      var linked = def.AssignedModels();
      if (linked.length > 0) node.ref = attr(linked[0], Constants.AT_ID) || linked[0].GUID();
    }
    nodes.push(node);
  }

  // pass 2: edges. Control flow between functions/events/connectors; an edge
  // from an org unit to a function assigns the lane.
  for (var j = 0; j < occs.length; j++) {
    var src = occs[j], out = src.OutEdges(Constants.EDGES_ALL);
    for (var k = 0; k < out.length; k++) {
      var dst = out[k].TargetObjOcc();
      var sk = KIND[src.ObjDef().TypeNum()], dk = KIND[dst.ObjDef().TypeNum()];
      var sid = src.ObjOccGUID ? src.ObjOccGUID() : src.ObjDef().GUID();
      var did = dst.ObjOccGUID ? dst.ObjOccGUID() : dst.ObjDef().GUID();
      if (sk === "lane" && dk === "function") { laneOf[did] = src.ObjDef().GUID(); continue; }
      if (dk === "lane" && sk === "function") { laneOf[sid] = dst.ObjDef().GUID(); continue; }
      if (!sk || !dk || sk === "lane" || dk === "lane") continue;
      edges.push({ from: sid, to: did });
    }
  }
  for (var n = 0; n < nodes.length; n++) {
    if (laneOf[nodes[n].id]) nodes[n].lane = laneOf[nodes[n].id];
  }

  return {
    version: 1,
    process: {
      id: attr(model, Constants.AT_ID) || model.GUID(),
      name: model.Name(-1),
      owner: attr(model, Constants.AT_PERSON_RESPONS)
    },
    lanes: lanes, nodes: nodes, edges: edges
  };
}

function main() {
  var models = ArisData.getSelectedModels(), out = [];
  for (var i = 0; i < models.length; i++) out.push(exportModel(models[i]));
  var doc = out.length === 1 ? out[0] : { version: 1, processes: out };
  var text = JSON.stringify(doc, null, 2);
  var outfile = Context.createOutputObject(Constants.OUTTEXT, Context.getSelectedFile());
  outfile.OutputTxt(text);
  outfile.WriteReport();
}

main();
