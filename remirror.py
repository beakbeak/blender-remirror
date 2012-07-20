bl_info = {
  "name": "Remirror",
  "author": "Philip Lafleur",
  "version": (1, 0),
  "blender": (2, 6, 3),
  "location": "View3D > Tools",
  "description": "Update symmetry of a mirrored object without changing topology.",
  "warning": "",
  "wiki_url": "",
  "tracker_url": "",
  "category": "Mesh"}

import bpy
import bmesh

class Remirror (bpy.types.Operator):
  bl_idname = "mesh.remirror"
  bl_label = "Remirror"
  bl_description = "Update symmetry of a mirrored object without changing topology"

  @classmethod
  def poll (cls, context):
    obj = context.active_object
    return (obj and obj.type == 'MESH' and context.mode == 'EDIT_MESH')

  def invoke (self, context, event):
    self.action (context)
    return {'FINISHED'}

  def execute (self, context):
    self.action (context)
    return {'FINISHED'}

  def action (self, context):
#    save_global_undo = bpy.context.user_preferences.edit.use_global_undo
#    bpy.context.user_preferences.edit.use_global_undo = False
    obj = bpy.context.active_object
    mesh = obj.data
    remirror (mesh)
#    bpy.context.user_preferences.edit.use_global_undo = save_global_undo
#    bpy.ops.object.editmode_toggle()
#    bpy.ops.object.editmode_toggle()


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
    raise ValueError ("len (edge.link_loops) != 1 or 2")

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
    raise ValueError ("len (edge.link_loops) != 1 or 2")


def edgeIndex (next_edge, v, e_start, index):
  edge = e_start
  while index > 0:
    edge = next_edge (v, edge)
    index = index - 1
  return edge

def edgeIndexCCW (v, e_start, index):
  return edgeIndex (nextEdgeCCW, v, e_start, index)

def edgeIndexCW (v, e_start, index):
  return edgeIndex (nextEdgeCW, v, e_start, index)


def followPath (edge_index, v, e_start, path):
  for index, unused in path:
    e_start = edge_index (v, e_start, index)
    v = e_start.other_vert (v)
  return v

def followPathCCW (v, e_start, path):
  return followPath (edgeIndexCCW, v, e_start, path)

def followPathCW (v, e_start, path):
  return followPath (edgeIndexCW, v, e_start, path)


# visit all unvisited subvertices of a particular vertex in the selected cycle
def visitVerts (v, e_start, visitor):
  index = 0
  edge = e_start
  path = []

  while True:
    index += 1
    edge = nextEdgeCCW (v, edge)

    if edge.select:
      return

    v = edge.other_vert (v)
    if v.tag:
      v = edge.other_vert (v)
      continue

    path.append ((index, edge))
    visitor (v, path)
    v.tag = True

    index = 0
    while path:
      index += 1
      edge = nextEdgeCCW (v, edge)

      if edge is path[-1][1] or edge.select:
        index = path[-1][0]
        edge = path[-1][1]
        v = edge.other_vert (v)
        del path[-1]
        continue

      v = edge.other_vert (v)
      if v.tag or v.select:
        v = edge.other_vert (v)
        continue

      path.append ((index, edge))
      visitor (v, path)
      v.tag = True

      index = 0

def updateVerts (v_start, e_start):
  def updateVert (v_original, path):
    v_mirror = followPathCW (v_start, e_start, path)
    v_mirror.co.x = -v_original.co.x
    v_mirror.co.y = v_original.co.y
    v_mirror.co.z = v_original.co.z

  visitVerts (v_start, e_start, updateVert)


def startingVertex (edge):
  if len (edge.link_loops) != 2:
    raise ValueError ("edge with loops != 2 selected")

  if edge.link_loops[0].face.calc_center_median ().x > 0.:
    return edge.link_loops[0].vert
  elif edge.link_loops[1].face.calc_center_median ().x > 0.:
    return edge.link_loops[1].vert
  else:
    raise ValueError ("edge with both connected faces' x <= 0 selected")


def remirror (mesh):
  bm = bmesh.from_edit_mesh (mesh)
  for v in bm.verts:
    v.tag = False
    if v.select:
      v.co.x = 0.

  for e in bm.edges:
    if e.select:
      updateVerts (startingVertex (e), e)

  for v in bm.verts:
    v.tag = False

  del bm
  mesh.update (calc_tessface = True)


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
