bl_info = {
  "name": "Remirror",
  "author": "Philip Lafleur",
  "version": (0, 1),
  "blender": (2, 6, 3),
  "location": "View3D > Tools",
  "description": ("Update symmetry of a mirrored mesh without "
                  "changing topology."),
  "warning": "",
  "wiki_url": "",
  "tracker_url": "",
  "category": "Mesh"}

import bpy
import bmesh

ERR_ASYMMETRY    = "Asymmetry encountered (central edge loop(s) not centered?)"
ERR_BAD_PATH     = "Couldn't follow edge path (inconsistent normals?)"
ERR_CENTRAL_LOOP = "Failed to find central edge loop(s). Please recenter."
ERR_FACE_COUNT   = "Encountered edge with more than 2 faces attached."

CENTRAL_LOOP_MARGIN = 1e-5

class Remirror (bpy.types.Operator):
  bl_idname      = "mesh.remirror"
  bl_label       = "Remirror"
  bl_description = ("Update symmetry of a mirrored mesh without "
                    "changing topology")
  bl_options     = {'REGISTER', 'UNDO'}

  # properties
  axis   = bpy.props.EnumProperty (
               name = "Axis",
               description = "Mirror axis",
               items = (('X', "X", "X Axis"),
                        ('Y', "Y", "Y Axis"),
                        ('Z', "Z", "Z Axis")))
  source = bpy.props.EnumProperty (
               name = "Source",
               description = "Half of mesh to be mirrored on the other half",
               items = (('POSITIVE', "Positive side", "Positive side"),
                        ('NEGATIVE', "Negative side", "Negative side")))

  @classmethod
  def poll (cls, context):
    obj = context.active_object
    return (obj and obj.type == 'MESH' and context.mode == 'EDIT_MESH')

  def execute (self, context):
    mesh = bpy.context.active_object.data

    try:
      remirror (mesh, {'X': 0, 'Y': 1, 'Z': 2}[self.axis], self.source)
    except ValueError as e:
      self.report ({'ERROR'}, str (e))

    return {'FINISHED'}


def nextEdgeCCW (v, e_prev):
  if len (e_prev.link_loops) == 2:
    # XXX: assumes continuous normals
    if e_prev.link_loops[0].vert is v:
      return e_prev.link_loops[0].link_loop_prev.edge
    return e_prev.link_loops[1].link_loop_prev.edge

  elif len (e_prev.link_loops) == 1:
    # XXX: assumes only two single-loop edges per vertex
    if e_prev.link_loops[0].vert is v:
      return e_prev.link_loops[0].link_loop_prev.edge
    for edge in v.link_edges:
      if len (edge.link_loops) == 1 and edge is not e_prev:
        return edge

  else:
    raise ValueError (ERR_FACE_COUNT)

def nextEdgeCW (v, e_prev):
  if len (e_prev.link_loops) == 2:
    # XXX: assumes continuous normals
    if e_prev.link_loops[0].vert is not v:
      return e_prev.link_loops[0].link_loop_next.edge
    return e_prev.link_loops[1].link_loop_next.edge

  elif len (e_prev.link_loops) == 1:
    # XXX: assumes only two single-loop edges per vertex
    if e_prev.link_loops[0].vert is not v:
      return e_prev.link_loops[0].link_loop_next.edge
    for edge in v.link_edges:
      if len (edge.link_loops) == 1 and edge is not e_prev:
        return edge

  else:
    raise ValueError (ERR_FACE_COUNT)


def visitMirrorVerts (v_start, e_start, visitor):
  er = e_start
  el = e_start
  vr = v_start
  vl = v_start
  path = [(er, el)]

  while path:
    er = nextEdgeCCW (vr, er)
    el = nextEdgeCW (vl, el)

    if er is path[-1][0] or er.tag:
      if not (el is path[-1][1] or el.tag):
        raise ValueError (ERR_ASYMMETRY)
      er = path[-1][0]
      el = path[-1][1]
      vr = er.other_vert (vr)
      vl = el.other_vert (vl)
      path.pop ()
      continue

    if el is path[-1][1] or el.tag:
      raise ValueError (ERR_ASYMMETRY)

    vr = er.other_vert (vr)
    if vr is None:
      raise ValueError (ERR_BAD_PATH)
    if vr.tag:
      vr = er.other_vert (vr)
      continue

    vl = el.other_vert (vl)
    if vl is None:
      raise ValueError (ERR_BAD_PATH)
    if vl.tag:
      raise ValueError (ERR_ASYMMETRY)

    path.append ((er, el))
    visitor (vr, vl)
    vr.tag = True

def updateVerts (v_start, e_start, axis, source):
  def updatePositive (v_right, v_left):
    v_left.co = v_right.co
    v_left.co[axis] = -v_right.co[axis]

  def updateNegative (v_right, v_left):
    v_right.co = v_left.co
    v_right.co[axis] = -v_left.co[axis]

  visitMirrorVerts (
      v_start, e_start,
      updatePositive if source == 'POSITIVE' else updateNegative)

def checkVerts (v_start, e_start):
  def checkVert (v_right, v_left):
    pass

  visitMirrorVerts (v_start, e_start, checkVert)


def tagCentralEdgePath (v, e):
  while True:
    e.tag = True

    if len (v.link_edges) % 2:
      if len (v.link_faces) == len (v.link_edges):
        raise ValueError (ERR_CENTRAL_LOOP)
      else:
        return

    for i in range (len (v.link_edges) // 2):
      e = nextEdgeCCW (v, e)

    v = e.other_vert (v)
    if v is None:
      raise ValueError (ERR_BAD_PATH)

    if e.tag:
      return

def tagCentralLoops (bm, axis):
  for v in bm.verts:
    v.tag = False
  for e in bm.edges:
    e.tag = False

  verts = []
  edges = []

  for v in bm.verts:
    if v.co[axis] < CENTRAL_LOOP_MARGIN and v.co[axis] > -CENTRAL_LOOP_MARGIN:
      v.tag = True
      verts.append (v)

  for v in verts:
    for e in v.link_edges:
      if e.other_vert (v).tag:
        e.tag = True
        edges.append (e)

  for v in verts:
    v.tag = False

  if not (edges and verts):
    raise ValueError (ERR_CENTRAL_LOOP)

  for e in edges:
    tagCentralEdgePath (e.verts[0], e)
    tagCentralEdgePath (e.verts[1], e)


def startingVertex (edge, axis):
  if len (edge.link_loops) != 2:
    raise ValueError (ERR_FACE_COUNT)

  loops = sorted (edge.link_loops,
                  key = lambda loop: loop.face.calc_center_median ()[axis])

  return loops[-1].vert

def remirror (mesh, axis, source):
  bm = bmesh.from_edit_mesh (mesh)

  try:
    tagCentralLoops (bm, axis)

    for e in bm.edges:
      if e.tag:
        e.verts[0].tag = True
        e.verts[1].tag = True

    for e in bm.edges:
      if e.tag:
        checkVerts (startingVertex (e, axis), e)

    for v in bm.verts:
      v.tag = False
    for e in bm.edges:
      if e.tag:
        e.verts[0].tag = True
        e.verts[1].tag = True

    for e in bm.edges:
      if e.tag:
        updateVerts (startingVertex (e, axis), e, axis, source)

  except:
    for v in bm.verts:
      v.tag = False
    for e in bm.edges:
      e.tag = False
    raise

  for e in bm.edges:
    if e.tag:
      e.verts[0].co[axis] = 0.
      e.verts[1].co[axis] = 0.

  for v in bm.verts:
    v.tag = False
  for e in bm.edges:
    e.tag = False


def register ():
  bpy.utils.register_class (Remirror)

def unregister ():
  bpy.utils.unregister_class (Remirror)


if __name__ == "__main__":
  register ()
