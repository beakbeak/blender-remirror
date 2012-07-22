# <pep8-80 compliant>

bl_info = {
  "name": "Remirror",
  "author": "Philip Lafleur",
  "version": (0, 1),
  "blender": (2, 6, 3),
  "location": "View3D > Tools",
  "description": ("Update symmetry of a mirrored object without "
                  "changing topology."),
  "warning": "",
  "wiki_url": "",
  "tracker_url": "",
  "category": "Mesh"}

import bpy
import bmesh

class Remirror (bpy.types.Operator):
  bl_idname = "mesh.remirror"
  bl_label = "Remirror"
  bl_description = ("Update symmetry of a mirrored object without "
                    "changing topology")
  bl_options = {'REGISTER', 'UNDO'}

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
      remirror (mesh, self.source)
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
    raise ValueError ("Encountered edge with more than 2 faces attached")

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
    raise ValueError ("Encountered edge with more than 2 faces attached")


# visit all unvisited subvertices of a particular vertex in the selected cycle
def visitMirrorVerts (v_start, e_start, visitor):
  er = e_start
  el = e_start
  vr = v_start
  vl = v_start
  path = [(er, el)]

  while path:
    er = nextEdgeCCW (vr, er)
    el = nextEdgeCW (vl, el)

    if er is path[-1][0] or er.select:
      er = path[-1][0]
      el = path[-1][1]
      vr = er.other_vert (vr)
      vl = el.other_vert (vl)
      del path[-1]
      continue

    vr = er.other_vert (vr)
    if vr.tag or vr.select:
      vr = er.other_vert (vr)
      continue
    vl = el.other_vert (vl)

    path.append ((er, el))
    visitor (vr, vl)
    vr.tag = True

def updateVerts (v_start, e_start, source = 'POSITIVE'):
  def updatePositive (v_right, v_left):
    v_left.co.x = -v_right.co.x
    v_left.co.y = v_right.co.y
    v_left.co.z = v_right.co.z

  def updateNegative (v_right, v_left):
    v_right.co.x = -v_left.co.x
    v_right.co.y = v_left.co.y
    v_right.co.z = v_left.co.z

  visitMirrorVerts (v_start, e_start,
      updatePositive if source == 'POSITIVE' else updateNegative)

def checkVerts (v_start, e_start):
  def checkVert (v_right, v_left):
    pass

  visitMirrorVerts (v_start, e_start, checkVert)


def startingVertex (edge, axis = 0):
  if len (edge.link_loops) != 2:
    raise ValueError ("Number of faces attached to selected edge is not 2")

  loops = sorted (edge.link_loops,
                  key = lambda loop: loop.face.calc_center_median ()[axis])

  return loops[-1].vert

def remirror (mesh, source = 'POSITIVE'):
  bm = bmesh.from_edit_mesh (mesh)

  try:
    for v in bm.verts:
      v.tag = False

    for e in bm.edges:
      if e.select:
        checkVerts (startingVertex (e), e)

    for v in bm.verts:
      v.tag = False

    for e in bm.edges:
      if e.select:
        updateVerts (startingVertex (e), e, source)

  except:
    for v in bm.verts:
      v.tag = False
    raise

  for v in bm.verts:
    v.tag = False
    if v.select:
      v.co.x = 0.

#  del bm
#  mesh.update (calc_tessface = True)


#def panel_func(self, context):
#  self.layout.label (text = "Inset Polygon:")
#  self.layout.operator ("mesh.insetpoly", text="Inset Polygon")


def register ():
  bpy.utils.register_class (Remirror)
#  bpy.types.VIEW3D_PT_tools_meshedit.append(panel_func)


def unregister ():
  bpy.utils.unregister_class (Remirror)
#  bpy.types.VIEW3D_PT_tools_meshedit.remove(panel_func)


if __name__ == "__main__":
  register ()
