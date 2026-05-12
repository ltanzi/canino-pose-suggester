"""Generate poses/{1..5}.json placed in the elevator photo's perspective.

Canvas: viewBox 0 0 500 800, behind which the elevator photo is shown via
preserveAspectRatio="xMidYMid slice" (photo scaled to 600x800, cropped 50 each
side). All figure coordinates are baked at generation time using a simple
single-point-perspective projection.

World coords:
    x ∈ [0, 1]   left-to-right (0 = left side wall, 1 = right side wall)
    z ∈ [0, 1]   back-to-front (0 = touching back wall, 1 = at the door)

The renderer doesn't know about perspective — the JSON contains absolute
viewBox coords already.

Run from project root:
    python3 scripts/generate_poses.py
"""

import json
import os

# ---------------------------------------------------------------------------
# Perspective parameters (eyeballed from the elevator photo)
# ---------------------------------------------------------------------------
# Floor trapezoid in viewBox coords (y grows downward).
# Measured from user's annotated photo (references/empty_elevator_guidelines.png):
#   Back-left  (651, 2573)  Back-right  (1577, 2573)
#   Front-left (497, 2887)  Front-right (1698, 2887)
# Converted to viewBox via photo→viewBox map for xMidYMid slice:
#   vx = (px / 2166) * 600 - 50, vy = (py / 2888) * 800
# The visible floor is only ~87px tall at the bottom of the 800-tall canvas —
# depth perception comes mostly from figure SIZE, not from y position.
Y_BACK = 713
Y_FRONT = 800
X_BACK_LEFT = 130
X_BACK_RIGHT = 387
X_FRONT_LEFT = 88
X_FRONT_RIGHT = 420

# Figure scale at depth extremes (1.0 = full local-template height of 458).
# Calibrated against the back wall height in the photo: the back wall spans
# y=172..713 (541 px) for a real 2.5m wall, so a 1.75m person at the back is
# ~379 px → scale ~0.83. Front compressed for visual balance.
SCALE_BACK = 0.83
SCALE_FRONT = 1.40


def project(x, z):
    """(x, z) in [0,1] -> (foot_x_image, foot_y_image, scale)."""
    left = X_BACK_LEFT + z * (X_FRONT_LEFT - X_BACK_LEFT)
    right = X_BACK_RIGHT + z * (X_FRONT_RIGHT - X_BACK_RIGHT)
    foot_x = left + x * (right - left)
    foot_y = Y_BACK + z * (Y_FRONT - Y_BACK)
    scale = SCALE_BACK + z * (SCALE_FRONT - SCALE_BACK)
    return foot_x, foot_y, scale


def wall_x(side, z):
    """X coordinate of left (side='left') or right side wall at depth z."""
    if side == "left":
        return X_BACK_LEFT + z * (X_FRONT_LEFT - X_BACK_LEFT)
    return X_BACK_RIGHT + z * (X_FRONT_RIGHT - X_BACK_RIGHT)


# ---------------------------------------------------------------------------
# Face helpers — eyes + smile for front-facing heads, two-line nose for profiles.
# Positions are computed relative to the head center so they scale with head radius.
# ---------------------------------------------------------------------------
def face(cx=0, cy=-430, r=28, tilt="forward"):
    """Eyes + a soft smile inside a front-facing head.

    tilt='forward' (default): centered face — the head is upright.
    tilt='up':                 features shifted toward the top of the circle so
                               the empty lower half reads as a forward chin —
                               head tilted back, looking upward.
    """
    if tilt == "up":
        eye_y_off = -0.52
        smile_y_off = -0.08
    else:
        eye_y_off = -0.22
        smile_y_off = 0.32
    eye_y = cy + r * eye_y_off
    eye_inner = r * 0.22
    eye_outer = r * 0.42
    smile_y = cy + r * smile_y_off
    smile_top = smile_y - r * 0.16
    smile_w = r * 0.40
    return [
        ("leftEye",  cx - eye_outer, eye_y,    cx - eye_inner, eye_y),
        ("rightEye", cx + eye_inner, eye_y,    cx + eye_outer, eye_y),
        ("smileL",   cx - smile_w,   smile_top, cx,            smile_y),
        ("smileR",   cx,             smile_y,   cx + smile_w,  smile_top),
    ]


def rotate_lines(lines, cx, cy, direction="ccw"):
    """Rotate line endpoints 90° around (cx, cy).
    direction='ccw' (counter-clockwise visually): bottom -> right, top -> left.
    direction='cw': mirror of CCW.
    """
    rotated = []
    for line in lines:
        id_, x1, y1, x2, y2 = line
        if direction == "ccw":
            r1 = (cx + (y1 - cy), cy - (x1 - cx))
            r2 = (cx + (y2 - cy), cy - (x2 - cx))
        else:
            r1 = (cx - (y1 - cy), cy + (x1 - cx))
            r2 = (cx - (y2 - cy), cy + (x2 - cx))
        rotated.append((id_, r1[0], r1[1], r2[0], r2[1]))
    return rotated


def nose(direction, cx=0, cy=-430, r=28):
    """Two-line ' > ' (right) or ' < ' (left) nose poking out of a profile head."""
    sign = 1 if direction == "right" else -1
    tip = (cx + sign * r * 1.40, cy)
    base_top = (cx + sign * r, cy - r * 0.10)
    base_bot = (cx + sign * r, cy + r * 0.10)
    return [
        ("noseTop", base_top[0], base_top[1], tip[0], tip[1]),
        ("noseBot", tip[0], tip[1], base_bot[0], base_bot[1]),
    ]


def face_profile(direction, cx=0, cy=-430, r=28):
    """Single eye + a side-view smile shifted to the facing side.
    The mouth's front corner lands exactly on the head's circumference so the
    lip line meets the silhouette of the face (no visible gap).
    """
    sign = 1 if direction == "right" else -1
    eye_y = cy - r * 0.20
    eye_cx = cx + sign * r * 0.42
    eye_half = r * 0.08
    mouth_y = cy + r * 0.26
    mouth_half = r * 0.12
    mouth_tilt = r * 0.10
    # Place the front mouth corner exactly on the head's circumference so the
    # line ends right at the silhouette (matches the legend).
    front_dy = mouth_y + mouth_tilt - cy
    front_dx_on_circle = (r * r - front_dy * front_dy) ** 0.5
    mouth_cx = cx + sign * (front_dx_on_circle - mouth_half)
    return [
        ("eye",   eye_cx - eye_half, eye_y, eye_cx + eye_half, eye_y),
        ("mouth",
         mouth_cx - sign * mouth_half, mouth_y - mouth_tilt,
         mouth_cx + sign * mouth_half, mouth_y + mouth_tilt),
    ]


# ---------------------------------------------------------------------------
# Local body templates
# Origin at the figure's floor contact point. Body extends upward = negative y.
# Total standing height: 458 units in local coords.
# ---------------------------------------------------------------------------
T_STANDING = {
    "head": (0, -430, 28),
    "facing": "front",
    "lines": [
        ("torso",    0, -402, 0, -245),
        ("leftArm",  0, -380, -32, -295),
        ("rightArm", 0, -380, 32, -295),
        ("leftLeg",  0, -245, -20, 0),
        ("rightLeg", 0, -245, 20, 0),
    ] + face(0, -430, 28),
}

T_ARMS_UP = {
    "head": (0, -430, 28),
    "facing": "front",
    "lines": [
        ("torso",    0, -402, 0, -245),
        ("leftArm",  0, -380, -110, -540),
        ("rightArm", 0, -380, 110, -540),
        ("leftLeg",  0, -245, -20, 0),
        ("rightLeg", 0, -245, 20, 0),
    ] + face(0, -430, 28),
}

T_LEANING_HIP = {
    "head": (5, -430, 28),
    "facing": "front",
    "lines": [
        ("torso",    5, -402, -5, -245),
        ("armHip",   5, -375, -45, -250),
        ("armHip2", -45, -250, -15, -230),
        ("armDown",  5, -375, 40, -290),
        ("leftLeg", -5, -245, -25, 0),
        ("rightLeg",-5, -245, 20, 0),
    ] + face(5, -430, 28),
}

T_CROUCHING = {
    "head": (0, -260, 26),
    "facing": "front",
    "lines": [
        ("torso",   0, -234, 0, -140),
        ("leftArm", 0, -220, -32, -145),
        ("rightArm",0, -220, 32, -145),
        ("thighL",  0, -140, -25, -70),
        ("footL",   -25, -70, -25, 0),
        ("thighR",  0, -140, 25, -70),
        ("footR",   25, -70, 25, 0),
    ] + face(0, -260, 26),
}

T_SITTING = {
    "head": (0, -178, 26),
    "facing": "front",
    "lines": [
        ("torso",     0, -152, 0, -63),
        ("leftArm",   0, -128, -32, -58),
        ("rightArm",  0, -128, 32, -58),
        ("legCrossL", 0, -63, -45, 0),
        ("legCrossR", 0, -63, 45, 0),
    ] + face(0, -178, 26),
}

T_LOOKING_UP = {
    "head": (0, -440, 28),
    "facing": "front",
    "lines": [
        ("torso",     0, -407, 0, -245),
        ("leftArm",   0, -380, -35, -255),
        ("rightArm",  0, -380, 35, -255),
        ("leftLeg",   0, -245, -20, 0),
        ("rightLeg",  0, -245, 20, 0),
    ] + face(0, -440, 28, tilt="up"),
}

T_PROFILE = {
    "head": (0, -430, 28),
    "facing": "front",  # rendered as plain outline; the face features convey direction
    "lines": [
        ("torso",      0, -402, 0, -245),
        ("armForward", 0, -375, 60, -255),
        ("armBack",    0, -375, -40, -250),
        ("legFront",   0, -245, 25, 0),
        ("legBack",    0, -245, -20, 0),
    ] + nose("right", 0, -430, 28) + face_profile("right", 0, -430, 28),
}

T_PROFILE_FACING_LEFT = {
    "head": (0, -430, 28),
    "facing": "front",
    "lines": [
        ("torso",      0, -402, 0, -245),
        ("armForward", 0, -375, -60, -255),
        ("armBack",    0, -375, 40, -250),
        ("legFront",   0, -245, -25, 0),
        ("legBack",    0, -245, 20, 0),
    ] + nose("left", 0, -430, 28) + face_profile("left", 0, -430, 28),
}


def place(template, x, z, dx=0, dy=0):
    """Project a local template onto the floor at (x, z), returning a figure dict.

    dx/dy shift the local origin (in local-template units, scaled by depth)
    — useful for stacking limbs on a leaning figure, etc.
    """
    fx, fy, s = project(x, z)
    bx = fx + dx * s
    by = fy + dy * s
    head_lx, head_ly, head_lr = template["head"]
    head = (bx + head_lx * s, by + head_ly * s, head_lr * s)
    lines = []
    for id_, lx1, ly1, lx2, ly2 in template["lines"]:
        lines.append((id_, bx + lx1 * s, by + ly1 * s, bx + lx2 * s, by + ly2 * s))
    return _make_fig(head, lines, z, facing=template.get("facing", "front"))


def _make_fig(head, lines, z, facing="front"):
    """Internal: build figure dict with rounded coords and stash z for sorting.

    `facing` controls how the head is rendered: 'front' = outline (face visible),
    'side'/'back' = filled (face away from camera).
    """
    head_dict = {
        "cx": round(head[0], 1),
        "cy": round(head[1], 1),
        "r":  round(head[2], 1),
    }
    if facing != "front":
        head_dict["facing"] = facing
    return {
        "_z": z,
        "head": head_dict,
        "lines": [
            {
                "id": id_,
                "x1": round(x1, 1),
                "y1": round(y1, 1),
                "x2": round(x2, 1),
                "y2": round(y2, 1),
            }
            for (id_, x1, y1, x2, y2) in lines
        ],
    }


# ---------------------------------------------------------------------------
# Direct-build helpers for poses that interact with elevator walls
# ---------------------------------------------------------------------------
def starfish(x, z):
    """Standing with arms + legs spread to the side walls at this depth."""
    fx, fy, s = project(x, z)
    head_cx, head_cy, head_r = fx, fy - 430 * s, 28 * s
    head = (head_cx, head_cy, head_r)
    shoulder_y = fy - 380 * s
    hip_y = fy - 245 * s
    left_x = wall_x("left", z)
    right_x = wall_x("right", z)
    return _make_fig(
        head,
        [
            ("torso",   fx, fy - 402 * s, fx, hip_y),
            ("armL",    fx, shoulder_y, left_x,  shoulder_y - 90 * s),
            ("armR",    fx, shoulder_y, right_x, shoulder_y - 90 * s),
            ("legL",    fx, hip_y, fx - 80 * s, fy),
            ("legR",    fx, hip_y, fx + 80 * s, fy),
        ] + face(head_cx, head_cy, head_r),
        z,
    )


def hands_on_walls(x, z):
    """Standing with arms extending horizontally to both side walls."""
    fx, fy, s = project(x, z)
    head_cx, head_cy, head_r = fx, fy - 430 * s, 28 * s
    head = (head_cx, head_cy, head_r)
    shoulder_y = fy - 380 * s
    hip_y = fy - 245 * s
    return _make_fig(
        head,
        [
            ("torso",   fx, fy - 402 * s, fx, hip_y),
            ("armL",    fx, shoulder_y, wall_x("left", z),  shoulder_y),
            ("armR",    fx, shoulder_y, wall_x("right", z), shoulder_y),
            ("leftLeg", fx, hip_y, fx - 20 * s, fy),
            ("rightLeg",fx, hip_y, fx + 20 * s, fy),
        ] + face(head_cx, head_cy, head_r),
        z,
    )


def back_against_wall(x, z, side="back"):
    """Standing with arms crossed, back to a wall. side: 'back' (default) or 'left'/'right'."""
    fx, fy, s = project(x, z)
    head_cx, head_cy, head_r = fx, fy - 430 * s, 28 * s
    head = (head_cx, head_cy, head_r)
    shoulder_y = fy - 380 * s
    hip_y = fy - 245 * s
    return _make_fig(
        head,
        [
            ("torso",     fx, fy - 402 * s, fx, hip_y),
            ("armCrossL", fx - 22 * s, fy - 320 * s, fx + 35 * s, fy - 340 * s),
            ("armCrossR", fx + 35 * s, fy - 315 * s, fx - 18 * s, fy - 340 * s),
            ("leftLeg",   fx, hip_y, fx - 20 * s, fy),
            ("rightLeg",  fx, hip_y, fx + 20 * s, fy),
        ] + face(head_cx, head_cy, head_r),
        z,
    )


def foot_on_wall(x, z, side="left"):
    """Standing near a side wall with one foot flat against it."""
    fx, fy, s = project(x, z)
    head_cx, head_cy, head_r = fx, fy - 430 * s, 28 * s
    head = (head_cx, head_cy, head_r)
    shoulder_y = fy - 380 * s
    hip_y = fy - 245 * s
    wall = wall_x(side, z)
    foot_up_x = wall
    foot_up_y = fy - 130 * s
    arm_l_x = fx + (-30 if side == "left" else 30) * s
    arm_r_x = fx + (45 if side == "left" else -45) * s
    return _make_fig(
        head,
        [
            ("torso",   fx, fy - 402 * s, fx, hip_y),
            ("leftArm", fx, shoulder_y, arm_l_x, fy - 295 * s),
            ("rightArm",fx, shoulder_y, arm_r_x, fy - 290 * s),
            ("legStand",fx, hip_y, fx, fy),
            ("legUp",   fx, hip_y, foot_up_x, foot_up_y),
        ] + face(head_cx, head_cy, head_r),
        z,
    )


def corner_knees_up(z, side="left"):
    """Tucked into a back corner, knees up."""
    x = 0.05 if side == "left" else 0.95
    fx, fy, s = project(x, z)
    sign = 1 if side == "left" else -1
    head_cx = fx + sign * 12 * s
    head_cy = fy - 175 * s
    head_r = 26 * s
    head = (head_cx, head_cy, head_r)
    return _make_fig(
        head,
        [
            ("torso",   head_cx, fy - 150 * s, head_cx + sign * 12 * s, fy - 65 * s),
            ("armWrap", head_cx + sign * 18 * s, fy - 130 * s,
                        head_cx + sign * 70 * s, fy - 80 * s),
            ("armWrap2",head_cx + sign * 70 * s, fy - 80 * s,
                        head_cx + sign * 50 * s, fy - 30 * s),
            ("thighL",  head_cx + sign * 12 * s, fy - 65 * s,
                        head_cx + sign * 70 * s, fy - 130 * s),
            ("shinL",   head_cx + sign * 70 * s, fy - 130 * s,
                        head_cx + sign * 70 * s, fy - 5 * s),
            ("thighR",  head_cx + sign * 12 * s, fy - 65 * s,
                        head_cx + sign * 50 * s, fy - 90 * s),
            ("shinR",   head_cx + sign * 50 * s, fy - 90 * s,
                        head_cx + sign * 50 * s, fy - 5 * s),
        ] + face(head_cx, head_cy, head_r),
        z,
    )


def mid_jump(x, z):
    """Both feet off the floor, arms up. Foot 'anchor' lifted ~120 local units."""
    fx, fy, s = project(x, z)
    lift = 160 * s
    head_cx, head_cy, head_r = fx, fy - 430 * s - lift, 28 * s
    head = (head_cx, head_cy, head_r)
    shoulder_y = fy - 380 * s - lift
    hip_y = fy - 245 * s - lift
    return _make_fig(
        head,
        [
            ("torso",   fx, fy - 402 * s - lift, fx, hip_y),
            ("armL",    fx, shoulder_y, fx - 110 * s, fy - 540 * s - lift),
            ("armR",    fx, shoulder_y, fx + 110 * s, fy - 540 * s - lift),
            ("legL",    fx, hip_y, fx - 25 * s, fy - 90 * s - lift),
            ("legR",    fx, hip_y, fx + 25 * s, fy - 90 * s - lift),
        ] + face(head_cx, head_cy, head_r),
        z,
    )


def sliding_down_wall(z, side="left"):
    """Knees half-bent, back pressed to a side wall, sliding down."""
    x = 0.08 if side == "left" else 0.92
    fx, fy, s = project(x, z)
    sign = 1 if side == "left" else -1
    head_cx, head_cy, head_r = fx, fy - 270 * s, 26 * s
    head = (head_cx, head_cy, head_r)
    return _make_fig(
        head,
        [
            ("torso",  fx, fy - 244 * s, fx + sign * 4 * s, fy - 130 * s),
            ("armL",   fx, fy - 220 * s, fx + sign * 40 * s, fy - 130 * s),
            ("armR",   fx, fy - 220 * s, fx - sign * 25 * s, fy - 125 * s),
            ("thighL", fx + sign * 4 * s, fy - 130 * s, fx + sign * 90 * s, fy - 100 * s),
            ("shinL",  fx + sign * 90 * s, fy - 100 * s, fx + sign * 90 * s, fy),
            ("thighR", fx + sign * 4 * s, fy - 130 * s, fx + sign * 70 * s, fy - 80 * s),
            ("shinR",  fx + sign * 70 * s, fy - 80 * s, fx + sign * 70 * s, fy),
        ] + face(head_cx, head_cy, head_r),
        z,
    )


def lying_feet_up_wall(z, side="right"):
    """Lying on the floor with feet pointing up against a side wall.
    Head sits above the body line; face is rotated so the chin points toward
    the body (CCW for body-extends-right, CW for body-extends-left).
    """
    x_head = 0.30 if side == "right" else 0.70
    fx, fy, s = project(x_head, z)
    sign = 1 if side == "right" else -1
    head_r = 26 * s
    head_cx = fx
    head_cy = fy - head_r * 0.70
    head = (head_cx, head_cy, head_r)
    wall = wall_x(side, z)
    body_end_x = fx + sign * 160 * s
    face_lines = rotate_lines(
        face(head_cx, head_cy, head_r), head_cx, head_cy,
        "ccw" if side == "right" else "cw",
    )
    return _make_fig(
        head,
        [
            ("torso",   fx + sign * head_r * 0.65, fy, body_end_x, fy),
            ("armUp",   fx + sign * 90 * s, fy, fx + sign * 95 * s, fy - 35 * s),
            ("armDown", fx + sign * 90 * s, fy, fx + sign * 95 * s, fy + 20 * s),
            ("thigh",   body_end_x, fy, body_end_x + sign * 60 * s, fy - 100 * s),
            ("shinL",   body_end_x + sign * 60 * s, fy - 100 * s, wall, fy - 180 * s),
            ("shinR",   body_end_x + sign * 60 * s, fy - 100 * s, wall, fy - 140 * s),
        ] + face_lines,
        z,
    )


def lying_flat(x_head, z, length=170, side="right"):
    """Lying on the floor, body extending horizontally.
    Head sits above the body line; face rotated so chin points toward body.
    """
    fx, fy, s = project(x_head, z)
    sign = 1 if side == "right" else -1
    head_r = 26 * s
    head_cx = fx
    head_cy = fy - head_r * 0.70
    head = (head_cx, head_cy, head_r)
    face_lines = rotate_lines(
        face(head_cx, head_cy, head_r), head_cx, head_cy,
        "ccw" if side == "right" else "cw",
    )
    return _make_fig(
        head,
        [
            ("torso",   fx + sign * head_r * 0.65, fy, fx + sign * length * s, fy),
            ("armUp",   fx + sign * 90 * s, fy, fx + sign * 100 * s, fy - 35 * s),
            ("armDown", fx + sign * 90 * s, fy, fx + sign * 95 * s, fy + 20 * s),
            ("legUp",   fx + sign * length * s, fy, fx + sign * (length + 50) * s, fy - 25 * s),
            ("legDown", fx + sign * length * s, fy, fx + sign * (length + 50) * s, fy + 15 * s),
        ] + face_lines,
        z,
    )


def high_five(x_left, x_right, z):
    """Two figures meeting one raised hand overhead in the center."""
    fxL, fyL, sL = project(x_left, z)
    fxR, fyR, sR = project(x_right, z)
    meet_y = (fyL + fyR) / 2 - 540 * (sL + sR) / 2
    meet_x = (fxL + fxR) / 2
    head_L = (fxL, fyL - 430 * sL, 28 * sL)
    head_R = (fxR, fyR - 430 * sR, 28 * sR)
    figL = _make_fig(
        head_L,
        [
            ("torso",    fxL, fyL - 402 * sL, fxL, fyL - 245 * sL),
            ("armUp",    fxL, fyL - 380 * sL, meet_x, meet_y),
            ("armDown",  fxL, fyL - 380 * sL, fxL - 35 * sL, fyL - 290 * sL),
            ("leftLeg",  fxL, fyL - 245 * sL, fxL - 20 * sL, fyL),
            ("rightLeg", fxL, fyL - 245 * sL, fxL + 20 * sL, fyL),
        ] + face(head_L[0], head_L[1], head_L[2]),
        z,
    )
    figR = _make_fig(
        head_R,
        [
            ("torso",    fxR, fyR - 402 * sR, fxR, fyR - 245 * sR),
            ("armUp",    fxR, fyR - 380 * sR, meet_x, meet_y),
            ("armDown",  fxR, fyR - 380 * sR, fxR + 35 * sR, fyR - 290 * sR),
            ("leftLeg",  fxR, fyR - 245 * sR, fxR - 20 * sR, fyR),
            ("rightLeg", fxR, fyR - 245 * sR, fxR + 20 * sR, fyR),
        ] + face(head_R[0], head_R[1], head_R[2]),
        z,
    )
    return [figL, figR]


# ---------------------------------------------------------------------------
# Pose libraries
# ---------------------------------------------------------------------------
def poses_1():
    return [
        ("1-standing-neutral",   "Standing neutral",                ["serious", "static", "neutral"],
         [place(T_STANDING, 0.5, 0.55)]),
        ("1-arms-up",            "Arms overhead",                   ["fun", "energetic"],
         [place(T_ARMS_UP, 0.5, 0.6)]),
        ("1-leaning-hip",        "Hand on hip",                     ["chill", "casual"],
         [place(T_LEANING_HIP, 0.45, 0.55)]),
        ("1-crouching",          "Crouching low",                   ["serious", "dynamic"],
         [place(T_CROUCHING, 0.5, 0.65)]),
        ("1-sitting-cross-legged","Sitting cross-legged",           ["chill", "static"],
         [place(T_SITTING, 0.5, 0.6)]),
        ("1-looking-up",         "Head tilted up",                  ["chill", "dreamy"],
         [place(T_LOOKING_UP, 0.5, 0.5)]),
        ("1-profile-side",       "Side profile",                    ["serious", "static"],
         [place(T_PROFILE, 0.5, 0.55)]),
        ("1-back-against-wall",  "Back against the wall",           ["serious", "static"],
         [back_against_wall(0.5, 0.12)]),
        ("1-foot-on-wall",       "Foot flat against the wall",      ["chill", "casual"],
         [foot_on_wall(0.18, 0.55, side="left")]),
        ("1-hands-on-opposite-walls","Hands pressing both side walls", ["fun", "dynamic"],
         [hands_on_walls(0.5, 0.65)]),
        ("1-sliding-down-wall",  "Sliding down the wall",           ["chill", "playful"],
         [sliding_down_wall(0.5, side="left")]),
        ("1-starfish",           "Starfish, limbs spread to walls", ["fun", "energetic"],
         [starfish(0.5, 0.55)]),
        ("1-close-up-portrait",  "Close-up, upper body fills frame",["serious", "intimate", "close-up"],
         [place(T_STANDING, 0.5, 1.6, dy=180)]),
        ("1-close-up-arms-up",   "Close-up, arms reaching up",      ["fun", "energetic", "close-up"],
         [place(T_ARMS_UP, 0.5, 1.7, dy=180)]),
        ("1-close-up-leaning",   "Close-up, hand on hip",           ["chill", "casual", "close-up"],
         [place(T_LEANING_HIP, 0.5, 1.55, dy=180)]),
        ("1-close-up-looking-up","Close-up, head tilted up",        ["dreamy", "intimate", "close-up"],
         [place(T_LOOKING_UP, 0.5, 1.9, dy=180)]),
        ("1-close-up-crouch",    "Close-up, crouched",              ["chill", "dynamic", "close-up"],
         [place(T_CROUCHING, 0.5, 1.3)]),
        ("1-stretching-tall",    "Stretched tall, arms reaching up",["fun", "energetic"],
         [place(T_ARMS_UP, 0.5, 0.95)]),
        ("1-far-back-small",     "Far back, tiny in the frame",     ["serious", "static", "neutral"],
         [place(T_STANDING, 0.5, 0.05)]),
        ("1-back-wall-leaning",  "Leaning casually at the back wall",["chill", "casual"],
         [place(T_LEANING_HIP, 0.5, 0.15)]),
        ("1-corner-right",       "Tucked into back-right corner",   ["chill", "intimate"],
         [corner_knees_up(0.25, side="right")]),
        ("1-corner-knees-up",    "Tucked into the corner, knees up",["chill", "intimate"],
         [corner_knees_up(0.25, side="left")]),
        ("1-mid-jump",           "Mid-jump, arms up",               ["fun", "energetic", "dynamic"],
         [mid_jump(0.5, 0.65)]),
        ("1-floor-feet-up-wall", "Lying on floor, feet up side wall",["chill", "playful"],
         [lying_feet_up_wall(0.6, side="right")]),
    ]


def poses_2():
    return [
        ("2-side-by-side", "Side by side, neutral", ["serious", "static"],
         [place(T_STANDING, 0.32, 0.55), place(T_STANDING, 0.68, 0.55)]),
        ("2-back-to-back", "Back to back", ["serious", "symmetric"],
         [place(T_STANDING, 0.40, 0.55), place(T_STANDING, 0.60, 0.55)]),
        ("2-leaning-on-other", "One leaning on the other", ["chill", "casual"],
         [place(T_STANDING, 0.35, 0.55), place(T_LEANING_HIP, 0.62, 0.55)]),
        ("2-both-arms-up", "Both arms overhead", ["fun", "energetic"],
         [place(T_ARMS_UP, 0.30, 0.55), place(T_ARMS_UP, 0.70, 0.55)]),
        ("2-stand-and-crouch", "One standing, one crouching", ["dynamic", "playful"],
         [place(T_STANDING, 0.30, 0.55), place(T_CROUCHING, 0.70, 0.65)]),
        ("2-sitting-together", "Sitting cross-legged together", ["chill", "static"],
         [place(T_SITTING, 0.30, 0.6), place(T_SITTING, 0.70, 0.6)]),
        ("2-mirrored-profile", "Facing each other in profile", ["serious", "symmetric"],
         [place(T_PROFILE, 0.30, 0.55), place(T_PROFILE_FACING_LEFT, 0.70, 0.55)]),
        ("2-opposite-walls", "Backs against opposite walls", ["serious", "symmetric"],
         [foot_on_wall(0.10, 0.5, side="left"), foot_on_wall(0.90, 0.5, side="right")]),
        ("2-one-pressed-to-wall", "One pinning the other to the back wall", ["dynamic", "playful"],
         [back_against_wall(0.55, 0.15), place(T_STANDING, 0.35, 0.45)]),
        ("2-one-floor-one-crouch", "One lying, one crouching", ["chill", "intimate"],
         [lying_flat(0.20, 0.7, length=170, side="right"), place(T_CROUCHING, 0.70, 0.65)]),
        ("2-high-five-mid-air", "High five overhead", ["fun", "energetic"],
         high_five(0.30, 0.70, 0.55)),
        ("2-foreheads-touching", "Foreheads almost touching", ["serious", "intimate"],
         [place(T_STANDING, 0.43, 0.55, dx=10), place(T_STANDING, 0.57, 0.55, dx=-10)]),
        ("2-one-up-one-floor", "One arms up, one lying with feet on wall", ["fun", "playful"],
         [place(T_ARMS_UP, 0.25, 0.5), lying_feet_up_wall(0.7, side="right")]),
        ("2-both-foot-on-wall", "Both with foot on opposite walls", ["chill", "symmetric"],
         [foot_on_wall(0.20, 0.55, side="left"), foot_on_wall(0.80, 0.55, side="right")]),
        ("2-close-and-far", "One close-up, one at the back", ["dynamic", "close-up"],
         [place(T_STANDING, 0.5, 0.15), place(T_LEANING_HIP, 0.35, 1.55, dy=180)]),
        ("2-close-up-pair", "Two side by side, close-up", ["fun", "close-up"],
         [place(T_STANDING, 0.30, 1.55, dy=180), place(T_STANDING, 0.70, 1.55, dy=180)]),
        ("2-close-up-mirror", "Two facing each other, close-up", ["serious", "intimate", "close-up"],
         [place(T_PROFILE, 0.32, 1.55, dy=180), place(T_PROFILE_FACING_LEFT, 0.68, 1.55, dy=180)]),
        ("2-close-up-stagger", "Two close-up, one slightly forward", ["dynamic", "close-up"],
         [place(T_STANDING, 0.40, 1.45, dy=180), place(T_ARMS_UP, 0.60, 1.85, dy=180)]),
        ("2-back-row", "Both side by side at the back wall", ["serious", "static"],
         [place(T_STANDING, 0.35, 0.15), place(T_STANDING, 0.65, 0.15)]),
        ("2-receding-line", "Receding through depth", ["dynamic", "static"],
         [place(T_STANDING, 0.55, 0.15), place(T_LEANING_HIP, 0.45, 0.70)]),
        ("2-talking-depth", "Two facing each other across depth", ["intimate", "close-up"],
         [place(T_PROFILE_FACING_LEFT, 0.70, 0.25), place(T_PROFILE, 0.30, 1.40, dy=180)]),
        ("2-mid-and-close", "One mid-depth, one close-up", ["dynamic", "close-up"],
         [place(T_STANDING, 0.55, 0.55), place(T_ARMS_UP, 0.30, 1.50, dy=180)]),
        ("2-both-close-arms-up", "Both close-up, arms reaching up", ["fun", "energetic", "close-up"],
         [place(T_ARMS_UP, 0.30, 1.55, dy=180), place(T_ARMS_UP, 0.70, 1.55, dy=180)]),
    ]


def poses_3():
    return [
        ("3-line-up", "Three in a line-up", ["serious", "static"],
         [place(T_STANDING, 0.20, 0.55), place(T_STANDING, 0.50, 0.55), place(T_STANDING, 0.80, 0.55)]),
        ("3-pyramid", "Front crouch, two behind", ["fun", "dynamic"],
         [place(T_STANDING, 0.30, 0.20), place(T_STANDING, 0.70, 0.20), place(T_CROUCHING, 0.5, 0.7)]),
        ("3-triangle-spread", "Triangle, points spread", ["fun", "dynamic"],
         [place(T_STANDING, 0.10, 0.65), place(T_STANDING, 0.5, 0.20), place(T_STANDING, 0.90, 0.65)]),
        ("3-one-front-two-back", "One front, two behind", ["serious", "static"],
         [place(T_STANDING, 0.30, 0.20), place(T_STANDING, 0.70, 0.20), place(T_STANDING, 0.5, 0.70)]),
        ("3-staggered-heights", "Stand, crouch, sit", ["chill", "dynamic"],
         [place(T_STANDING, 0.25, 0.55), place(T_CROUCHING, 0.55, 0.65), place(T_SITTING, 0.80, 0.60)]),
        ("3-huddle", "Tight huddle", ["serious", "intimate"],
         [place(T_STANDING, 0.42, 0.50, dx=5), place(T_STANDING, 0.50, 0.55), place(T_STANDING, 0.58, 0.50, dx=-5)]),
        ("3-circle-facing-out", "Circle, all facing outward", ["serious", "symmetric"],
         [place(T_PROFILE_FACING_LEFT, 0.20, 0.35), place(T_PROFILE, 0.80, 0.35), place(T_STANDING, 0.50, 0.70)]),
        ("3-three-walls", "One per wall", ["serious", "symmetric"],
         [back_against_wall(0.5, 0.12), foot_on_wall(0.12, 0.55, side="left"), foot_on_wall(0.88, 0.55, side="right")]),
        ("3-elevator-cross-section", "Sit, crouch, stand stack", ["chill", "dynamic"],
         [place(T_STANDING, 0.20, 0.35), place(T_CROUCHING, 0.50, 0.55), place(T_SITTING, 0.80, 0.70)]),
        ("3-two-sit-one-stand", "Two sitting, one standing between", ["chill", "casual"],
         [place(T_STANDING, 0.50, 0.30), place(T_SITTING, 0.25, 0.65), place(T_SITTING, 0.75, 0.65)]),
        ("3-all-arms-up", "All three with arms overhead", ["fun", "energetic"],
         [place(T_ARMS_UP, 0.20, 0.55), place(T_ARMS_UP, 0.50, 0.55), place(T_ARMS_UP, 0.80, 0.55)]),
        ("3-wave", "Wave of heights", ["fun", "dynamic"],
         [place(T_SITTING, 0.20, 0.60), mid_jump(0.50, 0.55), place(T_SITTING, 0.80, 0.60)]),
        ("3-different-directions", "Each facing a different wall", ["dynamic", "playful"],
         [place(T_PROFILE_FACING_LEFT, 0.20, 0.55), place(T_STANDING, 0.50, 0.55), place(T_PROFILE, 0.80, 0.55)]),
        ("3-floor-tangle", "Three on the floor in different positions", ["chill", "intimate"],
         [lying_flat(0.15, 0.7, length=160, side="right"), place(T_SITTING, 0.55, 0.60), place(T_SITTING, 0.85, 0.55)]),
        ("3-deep-stack", "Front close-up, middle, back", ["dynamic", "close-up"],
         [place(T_STANDING, 0.5, 0.15), place(T_LEANING_HIP, 0.30, 0.65), place(T_STANDING, 0.65, 1.55, dy=180)]),
        ("3-receding-stagger", "Three receding across depth", ["dynamic", "static"],
         [place(T_STANDING, 0.50, 0.10), place(T_LEANING_HIP, 0.30, 0.55), place(T_ARMS_UP, 0.70, 1.40, dy=180)]),
        ("3-back-row", "All three at the back wall", ["serious", "static"],
         [place(T_STANDING, 0.25, 0.15), place(T_STANDING, 0.50, 0.15), place(T_STANDING, 0.75, 0.15)]),
        ("3-tight-cluster-close", "Three clustered close-up", ["fun", "intimate", "close-up"],
         [place(T_STANDING, 0.32, 1.50, dy=180), place(T_STANDING, 0.50, 1.65, dy=180), place(T_STANDING, 0.68, 1.50, dy=180)]),
        ("3-diagonal", "Diagonal back-left to front-right", ["dynamic", "playful"],
         [place(T_STANDING, 0.20, 0.20), place(T_LEANING_HIP, 0.50, 0.60), place(T_ARMS_UP, 0.80, 1.30, dy=180)]),
        ("3-corner-trio", "One in each back corner, one front-center", ["serious", "symmetric"],
         [place(T_STANDING, 0.10, 0.20), place(T_STANDING, 0.90, 0.20), place(T_STANDING, 0.50, 0.85)]),
    ]


def poses_4():
    return [
        ("4-line-up", "Four in a line-up", ["serious", "static"],
         [place(T_STANDING, 0.15, 0.55), place(T_STANDING, 0.38, 0.55),
          place(T_STANDING, 0.62, 0.55), place(T_STANDING, 0.85, 0.55)]),
        ("4-two-by-two", "Front crouch, back stand", ["serious", "static"],
         [place(T_STANDING, 0.30, 0.20), place(T_STANDING, 0.70, 0.20),
          place(T_CROUCHING, 0.30, 0.70), place(T_CROUCHING, 0.70, 0.70)]),
        ("4-diamond", "Diamond formation", ["fun", "dynamic"],
         [place(T_STANDING, 0.50, 0.10), place(T_STANDING, 0.20, 0.45),
          place(T_STANDING, 0.80, 0.45), place(T_CROUCHING, 0.50, 0.78)]),
        ("4-arms-up-line", "All four arms up", ["fun", "energetic"],
         [place(T_ARMS_UP, 0.15, 0.55), place(T_ARMS_UP, 0.38, 0.55),
          place(T_ARMS_UP, 0.62, 0.55), place(T_ARMS_UP, 0.85, 0.55)]),
        ("4-staggered-heights", "Mixed heights", ["chill", "dynamic"],
         [place(T_STANDING, 0.15, 0.55), place(T_CROUCHING, 0.40, 0.65),
          place(T_STANDING, 0.65, 0.55), place(T_SITTING, 0.85, 0.65)]),
        ("4-huddle", "Tight huddle", ["serious", "intimate"],
         [place(T_STANDING, 0.38, 0.50, dx=5), place(T_STANDING, 0.46, 0.55),
          place(T_STANDING, 0.54, 0.55), place(T_STANDING, 0.62, 0.50, dx=-5)]),
        ("4-two-sit-two-stand", "Two sitting front, two standing back", ["chill", "casual"],
         [place(T_STANDING, 0.30, 0.20), place(T_STANDING, 0.70, 0.20),
          place(T_SITTING, 0.30, 0.70), place(T_SITTING, 0.70, 0.70)]),
        ("4-v-formation", "V formation", ["fun", "dynamic"],
         [place(T_STANDING, 0.50, 0.10), place(T_STANDING, 0.25, 0.40),
          place(T_STANDING, 0.75, 0.40), place(T_CROUCHING, 0.50, 0.75)]),
    ]


def poses_5():
    return [
        ("5-line-up", "Five in a line-up", ["serious", "static"],
         [place(T_STANDING, 0.10, 0.55), place(T_STANDING, 0.30, 0.55),
          place(T_STANDING, 0.50, 0.55), place(T_STANDING, 0.70, 0.55),
          place(T_STANDING, 0.90, 0.55)]),
        ("5-two-rows-stagger", "Two rows, staggered", ["serious", "static"],
         [place(T_STANDING, 0.20, 0.20), place(T_STANDING, 0.50, 0.20),
          place(T_STANDING, 0.80, 0.20),
          place(T_CROUCHING, 0.35, 0.72), place(T_CROUCHING, 0.65, 0.72)]),
        ("5-arrowhead", "Arrowhead V", ["fun", "energetic"],
         [place(T_STANDING, 0.50, 0.10), place(T_STANDING, 0.25, 0.32),
          place(T_STANDING, 0.75, 0.32),
          place(T_STANDING, 0.10, 0.55), place(T_STANDING, 0.90, 0.55)]),
        ("5-arms-up-line", "All five arms up", ["fun", "energetic"],
         [place(T_ARMS_UP, 0.10, 0.55), place(T_ARMS_UP, 0.30, 0.55),
          place(T_ARMS_UP, 0.50, 0.55), place(T_ARMS_UP, 0.70, 0.55),
          place(T_ARMS_UP, 0.90, 0.55)]),
        ("5-staggered-heights", "Mixed heights", ["chill", "dynamic"],
         [place(T_STANDING, 0.10, 0.45), place(T_CROUCHING, 0.30, 0.62),
          place(T_SITTING, 0.50, 0.70), place(T_CROUCHING, 0.70, 0.62),
          place(T_STANDING, 0.90, 0.45)]),
        ("5-cluster-casual", "Casual cluster", ["chill", "casual"],
         [place(T_STANDING, 0.30, 0.30), place(T_STANDING, 0.70, 0.30),
          place(T_LEANING_HIP, 0.50, 0.45),
          place(T_SITTING, 0.30, 0.72), place(T_SITTING, 0.70, 0.72)]),
        ("5-one-center-four-around", "One center, four flanking", ["serious", "symmetric"],
         [place(T_STANDING, 0.50, 0.30),
          place(T_STANDING, 0.15, 0.50), place(T_STANDING, 0.85, 0.50),
          place(T_STANDING, 0.30, 0.72), place(T_STANDING, 0.70, 0.72)]),
        ("5-half-sit-half-stand", "Mixed sit and stand", ["chill", "casual"],
         [place(T_STANDING, 0.20, 0.30), place(T_STANDING, 0.50, 0.30),
          place(T_STANDING, 0.80, 0.30),
          place(T_SITTING, 0.30, 0.72), place(T_SITTING, 0.70, 0.72)]),
    ]


# ---------------------------------------------------------------------------
# Build & write
# ---------------------------------------------------------------------------
def build(library):
    """Convert (id, name, tags, figures) tuples to pose dicts, sorted by depth
    so back-of-elevator figures render first (occluded by front ones)."""
    poses = []
    for id_, name, tags, figs in library:
        figs_sorted = sorted(figs, key=lambda f: f["_z"])
        for f in figs_sorted:
            f.pop("_z", None)
        poses.append({"id": id_, "name": name, "tags": tags, "figures": figs_sorted})
    return poses


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    poses_dir = os.path.join(here, "poses")
    os.makedirs(poses_dir, exist_ok=True)
    libraries = {1: poses_1(), 2: poses_2(), 3: poses_3(), 4: poses_4(), 5: poses_5()}
    for size, lib in libraries.items():
        poses = build(lib)
        path = os.path.join(poses_dir, f"{size}.json")
        with open(path, "w") as f:
            json.dump(poses, f, indent=2)
        print(f"Wrote {path}: {len(poses)} poses")


if __name__ == "__main__":
    main()
