/*
 * aris2puml — ARIS report script: EPC model → intermediate JSON (version 1).
 *
 * UNTESTED TEMPLATE — never run inside ARIS. Statically checked
 * (2026-09-04) against the ARIS Report Scripting Best Practices guide
 * (docs.aris.com, 10.0.27) and ARIS Community report code:
 *
 *   confirmed   ArisData.getSelectedModels, Model.ObjOccList, ObjOcc.ObjDef,
 *               ObjDef.TypeNum, ObjOcc.SymbolNum, ObjDef.AssignedModels
 *               (no longer called since 2026-11-27),
 *               ObjOcc.OutEdges/InEdges, CxnOcc.TargetObjOcc/SourceObjOcc,
 *               Constants.EDGES_ALL, OT_FUNC, OT_EVT, OT_RULE, ST_PRCS_IF,
 *               Context.getSelectedFile, Context.getSelectedLanguage
 *   unconfirmed Item.Attribute(...).getValue()/IsMaximized(),
 *               Context.createOutputObject(OUTTEXT)/OutputTxt/WriteReport,
 *               ST_OPR_XOR_1/AND_1/OR_1 (and the _2 variants), AT_ID,
 *               AT_PERSON_RESPONS, OT_ORG_UNIT, OT_POS, OT_PERS_TYPE,
 *               OT_INFO_CARR, OT_CLST, OT_TECH_TRM, OT_APPL_SYS_TYPE,
 *               CT_IS_INP_FOR, CT_HAS_OUT, CxnOcc.Cxn().TypeNum(), and
 *               whether OutEdges' argument is a direction or a kind filter
 *
 * Added 2026-11-27 (ieam-register decision 0022), checked against the
 * same guide's text and nothing else:
 *
 *   unconfirmed Model.SuperiorObjDefs() — the call meant to reach the
 *               definitions a model is assigned to. Found in neither the
 *               guide nor this repository: the name and what it returns
 *               are to be checked at A1b. processId() catches its failure
 *               and says so.
 *               Dialogs.MsgBox — the name is in the guide (its exception-
 *               reporting example); whether it shows anything when the
 *               report runs unattended is unconfirmed.
 *               ObjDef.GUID(), Model.GUID(), Name(-1) — called before this
 *               change too, classified in neither column above, and absent
 *               from the guide's text.
 *
 * Identity (decision 0022): a process is the function definition (OT_FUNC)
 * its EPC is assigned to, never the model. process.id is that definition's
 * REGISTER_ID_ATTRIBUTE, else its GUID; with no such definition, or more
 * than one carrying different ids, it is the model's GUID and a warning is
 * shown, so pumllint's GEN007 still fires on the footer. An interface's ref
 * is the REGISTER_ID_ATTRIBUTE of the interface occurrence's own
 * definition, else that definition's GUID. The process name and owner
 * still come from the model.
 *
 * Node ids are the object definition GUID plus the occurrence index in
 * the model ("<guid>#<n>"), so the same definition occurring twice yields
 * two nodes without any occurrence-GUID call, which could not be
 * confirmed to exist. Expect to adjust the unconfirmed names to your ARIS
 * version and method filter before first use. The JSON shape it writes is
 * the contract in aris2puml/readers/json_.py; keep that stable and
 * everything downstream works. For traversing through rule objects the
 * ARIS Community pattern (Seletkov, 2014: recurse over InEdges/OutEdges,
 * passing OT_RULE, with a visited map) is the reference.
 *
 * Usage (ARIS Architect): select one or more EPC models, run the report,
 * save the returned text as <model>.json, then:  aris2puml <model>.json
 */

// The attribute that carries the register id on a function definition:
// ieam-register sources.toml [system.aris] register_id_attribute, AT_ID by
// default (itself unconfirmed, above). An organisation that keeps the id
// in an attribute of its own names it here. Such an attribute is
// user-defined, and the guide says (3.4.10) its type number changes on a
// server restart and must be determined from its TypeGUID with the filter
// method UserDefinedAttributeTypeNum(); how to reach the filter from a
// report is not in the guide's text, so that line is the adopter's.
var REGISTER_ID_ATTRIBUTE = Constants.AT_ID;

var KIND = {};
KIND[Constants.OT_FUNC] = "function";
KIND[Constants.OT_EVT] = "event";
KIND[Constants.OT_RULE] = "connector";           // XOR / AND / OR — refined below
KIND[Constants.OT_ORG_UNIT] = "lane";
KIND[Constants.OT_POS] = "lane";
KIND[Constants.OT_PERS_TYPE] = "lane";           // role

// Information carriers, clusters, technical terms and application system
// types: not control flow; exported under "data", drawn only with --notes.
var DATA = {};
DATA[Constants.OT_INFO_CARR] = "document";
DATA[Constants.OT_CLST] = "information";
DATA[Constants.OT_TECH_TRM] = "information";
DATA[Constants.OT_APPL_SYS_TYPE] = "system";
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

var warnings = [];                                // shown once, after the output is written

// The process id (decision 0022): the register id of the one function
// definition the model is assigned to, else that definition's GUID; else the
// model's GUID, with a warning.
function processId(model) {
  var defs;
  try {
    defs = model.SuperiorObjDefs();               // UNCONFIRMED, see the header
  } catch (e) {
    warnings.push(model.Name(-1) + ": Model.SuperiorObjDefs() failed (" + e +
                  "); process id is the model's GUID");
    return model.GUID();
  }
  var ids = [], seen = {};
  for (var i = 0; i < defs.length; i++) {
    if (defs[i].TypeNum() != Constants.OT_FUNC) continue;
    var id = attr(defs[i], REGISTER_ID_ATTRIBUTE) || defs[i].GUID();
    if (!seen[id]) { seen[id] = true; ids.push(id); }
  }
  if (ids.length === 1) return ids[0];
  warnings.push(model.Name(-1) + ": " + (ids.length === 0
      ? "no function definition has this model assigned"
      : "function definitions with different ids have this model assigned (" + ids.join(", ") + ")") +
      "; process id is the model's GUID");
  return model.GUID();
}

function exportModel(model) {
  var lanes = [], laneIds = {}, nodes = [], edges = [], laneOf = {};
  var occs = model.ObjOccList();
  var occId = {};                                 // occurrence → stable node id
  for (var o = 0; o < occs.length; o++) occId[occs[o]] = occs[o].ObjDef().GUID() + "#" + o;

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
    var node = { id: occId[occ], kind: kind };
    if (kind !== "xor" && kind !== "and" && kind !== "or") node.name = def.Name(-1);
    if (kind === "function" && occ.SymbolNum() == INTERFACE_SYMBOL) {
      node.kind = "interface";
      node.ref = attr(def, REGISTER_ID_ATTRIBUTE) || def.GUID();   // the occurrence's own definition
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
      var sid = occId[src], did = occId[dst];
      if (sk === "lane" && dk === "function") { laneOf[did] = src.ObjDef().GUID(); continue; }
      if (dk === "lane" && sk === "function") { laneOf[sid] = dst.ObjDef().GUID(); continue; }
      if (!sk || !dk || sk === "lane" || dk === "lane") continue;
      edges.push({ from: sid, to: did });
    }
  }
  for (var n = 0; n < nodes.length; n++) {
    if (laneOf[nodes[n].id]) nodes[n].lane = laneOf[nodes[n].id];
  }

  // pass 3: data. An information carrier, cluster, technical term or
  // application system type connected to a function occurrence, either
  // way round; the connection type gives the role when it is input/output.
  var data = [];
  for (var d = 0; d < occs.length; d++) {
    var dOcc = occs[d], dKind = DATA[dOcc.ObjDef().TypeNum()];
    if (!dKind) continue;
    var cxns = dOcc.OutEdges(Constants.EDGES_ALL).concat(dOcc.InEdges(Constants.EDGES_ALL));
    for (var c = 0; c < cxns.length; c++) {
      var other = cxns[c].TargetObjOcc() === dOcc ? cxns[c].SourceObjOcc() : cxns[c].TargetObjOcc();
      if (KIND[other.ObjDef().TypeNum()] !== "function") continue;
      var item = { id: occId[dOcc], kind: dKind, name: dOcc.ObjDef().Name(-1), node: occId[other] };
      var ct = cxns[c].Cxn().TypeNum();
      if (ct == Constants.CT_IS_INP_FOR) item.role = "input";
      else if (ct == Constants.CT_HAS_OUT) item.role = "output";
      data.push(item);
    }
  }

  var doc = {
    version: 1,
    process: {
      id: processId(model),
      name: model.Name(-1),
      owner: attr(model, Constants.AT_PERSON_RESPONS)
    },
    lanes: lanes, nodes: nodes, edges: edges
  };
  if (data.length) doc.data = data;
  return doc;
}

function main() {
  var models = ArisData.getSelectedModels(), out = [];
  for (var i = 0; i < models.length; i++) out.push(exportModel(models[i]));
  var doc = out.length === 1 ? out[0] : { version: 1, processes: out };
  var text = JSON.stringify(doc, null, 2);
  var outfile = Context.createOutputObject(Constants.OUTTEXT, Context.getSelectedFile());
  outfile.OutputTxt(text);
  outfile.WriteReport();
  if (warnings.length) Dialogs.MsgBox("aris2puml export, process ids:\n" + warnings.join("\n"));
}

main();
