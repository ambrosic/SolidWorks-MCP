# SolidWorks MCP Agent Capability Tests

These tests evaluate an AI agent's ability to use the SolidWorks MCP server tools. Each test is self-contained and can be copy-pasted into a fresh Claude session connected to the MCP server. Tests are ordered from basic to advanced.

**How to use:** Copy a single test block (everything between the horizontal rules) into a new Claude conversation that has the SolidWorks MCP server connected. Verify the result in SolidWorks matches the expected outcome.

**Prerequisites:** SolidWorks must be running on the machine. The MCP server must be registered in Claude Desktop's config.

---

## Test 1: Basic Cube (Fundamental Workflow)

**What it tests:** The core workflow — creating a new part, opening a sketch, drawing a rectangle, exiting the sketch, and extruding.

**Prompt:**

```
Create a new part in SolidWorks. On the Front plane, sketch a 100mm x 100mm rectangle centered at the origin, then extrude it 100mm to create a cube.
```

**Expected outcome:**
- A new part document is created
- A sketch is opened on the Front plane
- A 100mm x 100mm rectangle is drawn centered at (0, 0)
- The sketch is exited (or extrusion handles it)
- An extrusion of 100mm depth is created
- Result: a cube visible in SolidWorks

**Tools that must be called (in order):**
1. `solidworks_new_part` or `solidworks_create_sketch` (which auto-creates a part)
2. `solidworks_create_sketch` with plane "Front"
3. `solidworks_sketch_rectangle` with width=100, height=100, centerX=0, centerY=0
4. `solidworks_create_extrusion` with depth=100

---

## Test 2: Circle Extrusion (Cylinder)

**What it tests:** Drawing a circle and extruding it into a cylinder.

**Prompt:**

```
Create a cylinder in SolidWorks. It should have a diameter of 50mm and a height of 75mm. Use the Top plane for the sketch.
```

**Expected outcome:**
- A circle with radius 25mm is sketched on the Top plane
- Extruded 75mm to form a cylinder
- Diameter of 50mm, height of 75mm

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Top"
2. `solidworks_sketch_circle` with radius=25
3. `solidworks_create_extrusion` with depth=75

---

## Test 3: Hexagonal Prism (Polygon + Extrusion)

**What it tests:** Using the polygon tool to create a regular hexagon and extruding it.

**Prompt:**

```
Create a hexagonal prism in SolidWorks. The hexagon should have a circumscribed radius of 30mm (center to vertex), and the prism should be 40mm tall. Sketch on the Front plane.
```

**Expected outcome:**
- A 6-sided polygon with radius 30mm at the origin
- Extruded 40mm
- Result: a hexagonal prism

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Front"
2. `solidworks_sketch_polygon` with radius=30, numSides=6
3. `solidworks_create_extrusion` with depth=40

---

## Test 4: Elliptical Disc

**What it tests:** Drawing an ellipse and extruding it into a thin disc.

**Prompt:**

```
Create an elliptical disc. The ellipse should have a semi-major axis of 40mm and a semi-minor axis of 25mm, centered at the origin on the Front plane. Extrude it 5mm thick.
```

**Expected outcome:**
- An ellipse centered at (0, 0) with majorRadius=40, minorRadius=25
- Extruded 5mm
- Result: a flat elliptical disc

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Front"
2. `solidworks_sketch_ellipse` with centerX=0, centerY=0, majorRadius=40, minorRadius=25
3. `solidworks_create_extrusion` with depth=5

---

## Test 5: Slot Feature

**What it tests:** Drawing a slot shape and extruding it.

**Prompt:**

```
Create an extruded slot shape. The slot should run horizontally from (-30, 0) to (30, 0) with a total width of 20mm. Sketch on the Front plane and extrude 10mm.
```

**Expected outcome:**
- A straight slot from (-30, 0) to (30, 0) with width=20
- Extruded 10mm
- Result: a stadium/slot-shaped solid

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Front"
2. `solidworks_sketch_slot` with x1=-30, y1=0, x2=30, y2=0, width=20
3. `solidworks_create_extrusion` with depth=10

---

## Test 6: Two Rectangles with Spacing (Spatial Awareness)

**What it tests:** The spatial positioning system — drawing a second shape relative to the first using the `spacing` parameter.

**Prompt:**

```
On the Front plane, draw two rectangles side by side. The first rectangle should be 40mm x 30mm centered at the origin. The second rectangle should be 40mm x 30mm placed 10mm to the right of the first one (10mm gap between them). Do not extrude, just create the sketch.
```

**Expected outcome:**
- First rectangle: 40x30mm at (0, 0)
- Second rectangle: 40x30mm positioned with a 10mm gap to the right of the first
  - The second rectangle's center should be at approximately (50, 0) — first right edge at 20, plus 10mm gap, plus 20mm half-width = center at 50
- Both shapes visible in the sketch

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Front"
2. `solidworks_sketch_rectangle` with width=40, height=30, centerX=0, centerY=0
3. `solidworks_sketch_rectangle` with width=40, height=30, spacing=10

---

## Test 7: Relative Positioning (Circle Offset from Rectangle)

**What it tests:** Using `relativeX`/`relativeY` to place a circle relative to a previous rectangle.

**Prompt:**

```
On the Front plane, draw a 60mm x 40mm rectangle at the origin. Then draw a circle with radius 15mm offset 80mm to the right and 20mm above the rectangle's center. Don't extrude.
```

**Expected outcome:**
- Rectangle: 60x40mm at (0, 0)
- Circle: radius 15mm at position (80, 20) — offset from rectangle center
- Both shapes in the sketch

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Front"
2. `solidworks_sketch_rectangle` with width=60, height=40, centerX=0, centerY=0
3. `solidworks_sketch_circle` with radius=15, relativeX=80, relativeY=20

---

## Test 8: Query Last Shape Info

**What it tests:** Using `solidworks_get_last_shape_info` to inspect the spatial tracking data.

**Prompt:**

```
On the Front plane, draw a 50mm x 30mm rectangle centered at (10, 20). Then tell me the exact bounding box and position information of that rectangle using the shape info tool.
```

**Expected outcome:**
- Rectangle drawn at (10, 20)
- Agent calls `solidworks_get_last_shape_info` and reports back:
  - Center: (10.0, 20.0)
  - Left: -15.0, Right: 35.0, Bottom: 5.0, Top: 35.0
  - Size: 50mm x 30mm

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Front"
2. `solidworks_sketch_rectangle` with width=50, height=30, centerX=10, centerY=20
3. `solidworks_get_last_shape_info`

---

## Test 9: Lines and Arcs

**What it tests:** Drawing lines and arcs with explicit coordinates.

**Prompt:**

```
On the Front plane, create a sketch with:
1. A straight line from (0, 0) to (50, 0)
2. A 3-point arc starting at (50, 0), ending at (50, 40), with the midpoint of the arc at (70, 20)
3. A straight line from (50, 40) back to (0, 40)
4. A straight line from (0, 40) back to (0, 0) to close the profile

Don't extrude yet.
```

**Expected outcome:**
- Four sketch entities forming a closed profile
- A rectangular-ish shape with one side replaced by an arc bulging outward
- All coordinates in mm

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Front"
2. `solidworks_sketch_line` with x1=0, y1=0, x2=50, y2=0
3. `solidworks_sketch_arc` with mode="3point", x1=50, y1=0, x2=50, y2=40, x3=70, y3=20
4. `solidworks_sketch_line` with x1=50, y1=40, x2=0, y2=40
5. `solidworks_sketch_line` with x1=0, y1=40, x2=0, y2=0

---

## Test 10: Spline Curve

**What it tests:** Creating a spline through multiple points.

**Prompt:**

```
On the Front plane, draw a smooth spline curve through these points (all in mm):
(0, 0), (20, 15), (40, -10), (60, 5), (80, 0)

Don't extrude. Just create the sketch with the spline.
```

**Expected outcome:**
- A smooth spline passing through all 5 points
- Visible as a wavy/smooth curve in the sketch

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Front"
2. `solidworks_sketch_spline` with points array containing the 5 points

---

## Test 11: Sketch Text

**What it tests:** Inserting text into a sketch.

**Prompt:**

```
On the Front plane, create a sketch and insert the text "SOLIDWORKS" at position (0, 0) with a font height of 10mm.
```

**Expected outcome:**
- Sketch text reading "SOLIDWORKS" placed at origin
- Text height set to 10mm

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Front"
2. `solidworks_sketch_text` with x=0, y=0, text="SOLIDWORKS", height=10

---

## Test 12: Construction Geometry

**What it tests:** Drawing a centerline (auto-construction) and toggling a normal line to construction.

**Prompt:**

```
On the Front plane, create a sketch with:
1. A vertical centerline from (0, -50) to (0, 50)
2. A horizontal line from (-30, 0) to (30, 0)
3. Toggle that horizontal line to construction geometry

Don't extrude.
```

**Expected outcome:**
- A vertical centerline (dashed, construction by default)
- A horizontal line that is toggled to construction geometry (also dashed)
- Neither line would form part of an extrusion profile

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Front"
2. `solidworks_sketch_centerline` with x1=0, y1=-50, x2=0, y2=50
3. `solidworks_sketch_line` with x1=-30, y1=0, x2=30, y2=0
4. `solidworks_sketch_toggle_construction` with x=0, y=0 (point on the line)

---

## Test 13: Sketch Constraint (Parallel Lines)

**What it tests:** Drawing two lines and applying a geometric constraint.

**Prompt:**

```
On the Front plane, draw two lines:
1. Line from (0, 0) to (50, 10)
2. Line from (0, 30) to (50, 25)

Then apply a PARALLEL constraint between them. Don't extrude.
```

**Expected outcome:**
- Two lines drawn
- After the parallel constraint is applied, both lines should become parallel
- SolidWorks adjusts the second line to match the angle of the first (or vice versa)

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Front"
2. `solidworks_sketch_line` with x1=0, y1=0, x2=50, y2=10
3. `solidworks_sketch_line` with x1=0, y1=30, x2=50, y2=25
4. `solidworks_sketch_constraint` with constraintType="PARALLEL" and entityPoints on both lines

---

## Test 14: Block with a Hole (Extrude + Cut-Extrude)

**What it tests:** The full additive + subtractive workflow — creating a solid body, then cutting a hole through it.

**Prompt:**

```
Create a rectangular block that is 80mm wide, 60mm tall, and 30mm deep. Then cut a circular hole through the center of the front face. The hole should have a diameter of 20mm and go 30mm deep (all the way through).
```

**Expected outcome:**
- A rectangular block (80x60mm sketch on Front plane, extruded 30mm)
- A circular hole (radius 10mm) cut through the center of the front face
- The cut should go all the way through (30mm deep)
- The hole should be centered on the front face of the block

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Front"
2. `solidworks_sketch_rectangle` with width=80, height=60, centerX=0, centerY=0
3. `solidworks_create_extrusion` with depth=30
4. `solidworks_create_sketch` with faceX, faceY, faceZ pointing to the front face (e.g., faceX=0, faceY=0, faceZ=0)
5. `solidworks_sketch_circle` with radius=10, centerX=0, centerY=0
6. `solidworks_create_cut_extrusion` with depth=30

---

## Test 15: Mass Properties Verification

**What it tests:** Creating a known geometry and querying its mass properties.

**Prompt:**

```
Create a 100mm x 100mm x 100mm cube (sketch on Front plane, centered at origin, extruded 100mm). Then get the mass properties. Report the volume and surface area.
```

**Expected outcome:**
- A 100mm cube is created
- Mass properties are retrieved
- Volume should be approximately 1,000,000 mm^3
- Surface area should be approximately 60,000 mm^2
- Center of mass should be at approximately (50, 50, 50) mm

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Front"
2. `solidworks_sketch_rectangle` with width=100, height=100, centerX=0, centerY=0
3. `solidworks_create_extrusion` with depth=100
4. `solidworks_get_mass_properties`

---

## Test 16: Right Plane Sketch

**What it tests:** Using a non-default reference plane.

**Prompt:**

```
Create a new part. Sketch a 40mm radius circle on the Right plane and extrude it 60mm.
```

**Expected outcome:**
- Sketch created on the Right plane (YZ plane)
- Circle with radius 40mm
- Extruded 60mm along the X axis
- Result: a cylinder oriented along X

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Right"
2. `solidworks_sketch_circle` with radius=40
3. `solidworks_create_extrusion` with depth=60

---

## Test 17: Pentagon with Inscribed Radius

**What it tests:** Polygon with the `inscribed` flag set to true.

**Prompt:**

```
On the Front plane, draw a regular pentagon with an inscribed circle radius of 25mm (the radius should measure to the midpoint of each side, not to a vertex). Center it at the origin. Extrude 15mm.
```

**Expected outcome:**
- A 5-sided regular polygon with inscribed=true and radius=25
- Centered at origin
- Extruded 15mm

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Front"
2. `solidworks_sketch_polygon` with numSides=5, radius=25, inscribed=true
3. `solidworks_create_extrusion` with depth=15

---

## Test 18: Center-Point Arc

**What it tests:** Using the arc tool in center-point mode.

**Prompt:**

```
On the Front plane, draw an arc using center-point mode. The arc center should be at (0, 0), with the start point at (30, 0) and the end point at (0, 30). Don't extrude.
```

**Expected outcome:**
- A quarter-circle arc with radius 30mm
- Centered at origin, sweeping from (30, 0) to (0, 30) counter-clockwise
- Visible as a 90-degree arc in the sketch

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Front"
2. `solidworks_sketch_arc` with mode="center", centerX=0, centerY=0, x1=30, y1=0, x2=0, y2=30

---

## Test 19: Rotated Ellipse

**What it tests:** Creating an ellipse with a rotation angle.

**Prompt:**

```
On the Front plane, draw an ellipse centered at the origin with a semi-major axis of 50mm and semi-minor axis of 20mm, rotated 45 degrees counterclockwise. Don't extrude.
```

**Expected outcome:**
- An ellipse at (0, 0)
- Major axis 50mm, minor axis 20mm
- Tilted 45 degrees from the horizontal
- The long axis should run from bottom-left to upper-right

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Front"
2. `solidworks_sketch_ellipse` with centerX=0, centerY=0, majorRadius=50, minorRadius=20, angle=45

---

## Test 20: Multi-Shape Sketch with Mixed Positioning

**What it tests:** Combining absolute and relative positioning in a single sketch with multiple shape types.

**Prompt:**

```
On the Front plane, create a sketch with three shapes in a horizontal row:
1. A 30mm x 30mm square centered at (-50, 0)
2. A circle with radius 15mm, placed 10mm to the right of the square (10mm gap)
3. A regular hexagon with radius 15mm, placed 10mm to the right of the circle (10mm gap)

Don't extrude. Just create the sketch with all three shapes.
```

**Expected outcome:**
- Square at (-50, 0): 30x30mm
- Circle 10mm to the right of the square's right edge, same vertical center
  - Square right edge = -35, so circle center at -35 + 10 + 15 = -10, y = 0
- Hexagon 10mm to the right of the circle's right edge, same vertical center
  - Circle right edge = 5, so hexagon center at 5 + 10 + 15 = 30, y = 0
- Three shapes in a neat row with equal gaps

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Front"
2. `solidworks_sketch_rectangle` with width=30, height=30, centerX=-50, centerY=0
3. `solidworks_sketch_circle` with radius=15, spacing=10
4. `solidworks_sketch_polygon` with radius=15, numSides=6, spacing=10

---

## Test 21: Sketch Point as Reference

**What it tests:** Creating sketch points for reference purposes.

**Prompt:**

```
On the Front plane, place three sketch points at (0, 0), (25, 25), and (50, 0). Then draw a line connecting (0, 0) to (50, 0). Don't extrude.
```

**Expected outcome:**
- Three sketch points visible at the specified coordinates
- A line from (0, 0) to (50, 0)
- The sketch points at (0, 0) and (50, 0) should visually coincide with the line endpoints

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Front"
2. `solidworks_sketch_point` with x=0, y=0
3. `solidworks_sketch_point` with x=25, y=25
4. `solidworks_sketch_point` with x=50, y=0
5. `solidworks_sketch_line` with x1=0, y1=0, x2=50, y2=0

---

## Test 22: Reverse Extrusion Direction

**What it tests:** Using the `reverse` flag on extrusion.

**Prompt:**

```
On the Front plane, draw a 40mm x 40mm square centered at the origin. Extrude it 50mm in the reverse direction (behind the Front plane).
```

**Expected outcome:**
- A 40x40mm rectangle on the Front plane
- Extruded 50mm in the reverse direction (negative Z)
- The solid should extend behind the Front plane

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Front"
2. `solidworks_sketch_rectangle` with width=40, height=40, centerX=0, centerY=0
3. `solidworks_create_extrusion` with depth=50, reverse=true

---

## Test 23: Corner-Defined Rectangle

**What it tests:** Defining a rectangle by two corner points instead of center + dimensions.

**Prompt:**

```
On the Front plane, draw a rectangle with one corner at (10, 10) and the opposite corner at (60, 40). Extrude it 20mm.
```

**Expected outcome:**
- A rectangle from corner (10, 10) to corner (60, 40)
- Width: 50mm, Height: 30mm
- Extruded 20mm

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Front"
2. `solidworks_sketch_rectangle` with x1=10, y1=10, x2=60, y2=40
3. `solidworks_create_extrusion` with depth=20

---

## Test 24: Complex Profile — Bracket Shape

**What it tests:** Agent's ability to decompose a real-world shape description into individual sketch entities and produce a closed profile.

**Prompt:**

```
Create an L-shaped bracket in SolidWorks. The vertical arm should be 60mm tall and 15mm wide. The horizontal arm should extend 40mm to the right and be 15mm wide. The overall shape looks like a capital "L". Sketch it on the Front plane using lines, then extrude it 10mm.

Use these coordinates for the outline:
- Start at (0, 0)
- Right to (40, 0)
- Up to (40, 15)
- Left to (15, 15)
- Up to (15, 60)
- Left to (0, 60)
- Down back to (0, 0)
```

**Expected outcome:**
- An L-shaped closed profile made of 6 lines
- Extruded 10mm to form a 3D L-bracket
- Profile should be fully closed for the extrusion to succeed

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Front"
2. Six `solidworks_sketch_line` calls forming the closed L-shape
3. `solidworks_create_extrusion` with depth=10

---

## Test 25: Multiple Constraints

**What it tests:** Applying multiple different constraint types in a single sketch.

**Prompt:**

```
On the Front plane:
1. Draw a horizontal line from (0, 0) to (50, 5) — note it's slightly angled
2. Draw a vertical line from (60, 0) to (65, 40) — also slightly off-vertical
3. Apply a HORIZONTAL constraint to the first line
4. Apply a VERTICAL constraint to the second line

Don't extrude.
```

**Expected outcome:**
- After applying HORIZONTAL, the first line should become perfectly horizontal (both endpoints at the same Y)
- After applying VERTICAL, the second line should become perfectly vertical (both endpoints at the same X)
- SolidWorks will snap the endpoints to satisfy the constraints

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Front"
2. `solidworks_sketch_line` (first line)
3. `solidworks_sketch_line` (second line)
4. `solidworks_sketch_constraint` with constraintType="HORIZONTAL" and entityPoints on the first line
5. `solidworks_sketch_constraint` with constraintType="VERTICAL" and entityPoints on the second line

---

## Test 26: Washer (Concentric Circles + Extrude + Cut)

**What it tests:** A practical part requiring additive extrusion followed by a subtractive cut to create a washer/ring shape.

**Prompt:**

```
Create a washer (flat ring):
1. On the Front plane, sketch a circle with outer radius 20mm centered at the origin. Extrude it 3mm.
2. Then create a sketch on the front face of the disc (at z=0) and draw a circle with radius 8mm centered at the origin. Cut-extrude it 3mm through the disc to create the hole.
```

**Expected outcome:**
- A flat disc (outer radius 20mm, 3mm thick)
- A through-hole in the center (radius 8mm)
- Result: a washer shape

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Front"
2. `solidworks_sketch_circle` with radius=20, centerX=0, centerY=0
3. `solidworks_create_extrusion` with depth=3
4. `solidworks_create_sketch` with faceX=0, faceY=0, faceZ=0
5. `solidworks_sketch_circle` with radius=8, centerX=0, centerY=0
6. `solidworks_create_cut_extrusion` with depth=3

---

## Test 27: Explicit New Part Before Sketch

**What it tests:** Using `solidworks_new_part` explicitly before starting a design.

**Prompt:**

```
Explicitly create a new blank part document first. Then open a sketch on the Top plane, draw a 35mm x 35mm square at the origin, and extrude it 35mm to make a cube.
```

**Expected outcome:**
- `solidworks_new_part` is called first
- Sketch on Top plane
- 35mm cube created

**Tools that must be called:**
1. `solidworks_new_part`
2. `solidworks_create_sketch` with plane "Top"
3. `solidworks_sketch_rectangle` with width=35, height=35, centerX=0, centerY=0
4. `solidworks_create_extrusion` with depth=35

---

## Test 28: Exit Sketch Explicitly

**What it tests:** Using `solidworks_exit_sketch` independently (not as part of extrusion).

**Prompt:**

```
On the Front plane, draw a 50mm radius circle at the origin. Exit the sketch without extruding. Then tell me you've exited the sketch successfully.
```

**Expected outcome:**
- Circle drawn in sketch
- `solidworks_exit_sketch` called explicitly
- Agent confirms sketch was exited
- No extrusion is performed

**Tools that must be called:**
1. `solidworks_create_sketch` with plane "Front"
2. `solidworks_sketch_circle` with radius=50
3. `solidworks_exit_sketch`

---

## Test 29: Describe-and-Build (Natural Language Comprehension)

**What it tests:** Agent's ability to interpret a natural language description (no explicit coordinates) and choose appropriate tool parameters.

**Prompt:**

```
I need a simple phone stand. Create a rectangular base that's about 80mm wide, 50mm deep, and 5mm thick. Then add a vertical wall on one end that's about 80mm wide, 30mm tall, and 5mm thick — this wall will prop up the phone.
```

**Expected outcome:**
- The agent should figure out the coordinate system and tool calls on its own
- A base plate created as an extrusion (e.g., 80x50mm rectangle, extruded 5mm)
- A vertical wall attached to one end (a second sketch on a face of the base, extruded upward)
- The result should look like a simple L-shaped phone stand
- The agent may need to use face-based sketching for the wall

**Evaluation criteria:**
- Does the agent plan a reasonable multi-step approach?
- Does it choose correct planes/faces for each feature?
- Are the dimensions roughly matching the request?
- Does the final shape function as described?

---

## Test 30: Error Recovery

**What it tests:** Agent's ability to handle and recover from errors (e.g., trying to extrude without a sketch).

**Prompt:**

```
Create a new part. Immediately try to extrude 50mm without creating a sketch first. After that fails, properly create a sketch on the Front plane with a 30mm x 30mm rectangle and extrude it 50mm.
```

**Expected outcome:**
- First extrusion attempt should fail (no sketch to extrude)
- Agent recognizes the error and recovers
- Agent creates a proper sketch with a rectangle
- Second extrusion succeeds
- Final result: a 30x30x50mm rectangular block

**Evaluation criteria:**
- Does the agent attempt the extrusion as requested?
- Does it handle the error gracefully?
- Does it successfully recover and complete the part?

---

## Scoring Guide

| Score | Meaning |
|-------|---------|
| **Pass** | All required tools were called with correct parameters; the result matches expected outcome |
| **Partial** | The right tools were called but with imprecise parameters (e.g., wrong center, missing positioning); the result is close but not exact |
| **Fail** | Wrong tools used, incorrect workflow order, missing critical steps, or SolidWorks errors not recovered |

### Category Breakdown

| Category | Tests | What's Evaluated |
|----------|-------|------------------|
| **Core Workflow** | 1, 2, 27, 28 | new_part, create_sketch, extrude, exit_sketch |
| **Sketch Entities** | 3, 4, 5, 9, 10, 11, 18, 19, 21, 23 | All shape tools (rectangle, circle, polygon, ellipse, slot, line, arc, spline, text, point) |
| **Spatial Positioning** | 6, 7, 8, 20 | spacing, relativeX/Y, centerX/Y, get_last_shape_info |
| **Constraints & Construction** | 12, 13, 25 | constraint, centerline, toggle_construction |
| **3D Operations** | 14, 15, 16, 22, 26 | extrusion, cut-extrusion, reverse, mass_properties, face sketching |
| **Complex / Natural Language** | 24, 29 | Multi-entity profiles, interpreting descriptions |
| **Error Handling** | 30 | Recovery from tool failures |
