"""Blender «Stacks» add-on constants"""

SUFFIX = '_trueops_ref'  # to be added to the names of the original objects used as hidden references.
__syncable = True  # to be used in INTERPOLATE to determine if the property is syncable. For STACKS_PropValues.
INTERPOLATE = {  # determines which attributes are used for defining the key attribute in the interpolation mode.
    "GENERATE": {
        "EXTRUDE": {
            "gen_extr_indval": ("value_min", "value_max"),
            "gen_extr_value": ("value_vec_min", "value_vec_max")
        },
        "SUBDIVIDE": {
            "gen_subd_cuts": ("value_min_int", "value_max_int"),
            "gen_subd_smooth": ("value_min", "value_max"),
        },
        "BEVEL": {
            "gen_b_offset_pct": ("value_min", "value_max"),
            "gen_b_offset": ("value_min", "value_max"),
        },
        "SOLIDIFY": {
            "gen_solidify": ("value_min", "value_max"),
        },
        "WIREFRAME": {
            "gen_wrf_thick": ("value_min", "value_max"),
        },
        "DUPLICATE": {
            "gen_grab": ("value_vec_min", "value_vec_max"),
            "gen_rotate": ("angle_vec_min", "angle_vec_max"),
            "gen_scale": ("scale_vec_min", "scale_vec_max", __syncable)
        },
        "INSET": {
            "gen_ins_thick": ("value_min", "value_max"),
            "gen_ins_depth": ("value_min2", "value_max2"),
        },
    },
    "DEFORM": {
        "SPHERE": {
            "sel_rand_ratio": ("value_min", "value_max"),
        },
        "RANDOMIZE": {
            "gen_extr_indval": ("value_min", "value_max"),
        },
        "SMOOTH": {
            "gen_subd_smooth": ("value_min", "value_max"),
        },
        "PUSH": {
            "gen_extr_indval": ("value_min", "value_max"),
        },
        "SHRINK": {
            "def_shrink_fac": ("value_min", "value_max"),
        },
        "SHEAR": {
            "def_shrink_fac": ("value_min", "value_max"),
        },
    },
    "SELECT": {
        "RANDOM": {
            "sel_rand_ratio": ("value_min", "value_max"),
            "sel_rand_seed": ("value_min_int", "value_max_int"),
        },
    },
    "TRANSFORM": {
        "GRAB": {
            "gen_grab": ("value_vec_min", "value_vec_max")
        },
        "ROTATE": {
            "gen_rotate": ("angle_vec_min", "angle_vec_max")
        },
        "SCALE": {
            "gen_scale": ("scale_vec_min", "scale_vec_max", __syncable)
        },
    },
    "ADD": {
        "PLANE": {
            "add_size": ("value_min", "value_max"),
            "gen_grab": ("value_vec_min", "value_vec_max"),
            "gen_rotate": ("angle_vec_min", "angle_vec_max"),
            "gen_scale": ("scale_vec_min", "scale_vec_max", __syncable),
        },
        "CUBE": {
            "add_size": ("value_min", "value_max"),
            "gen_grab": ("value_vec_min", "value_vec_max"),
            "gen_rotate": ("angle_vec_min", "angle_vec_max"),
            "gen_scale": ("scale_vec_min", "scale_vec_max", __syncable),
        },
        "CIRCLE": {
            "add_circ_verts": ("value_min_int", "value_max_int"),
            "add_radius": ("value_min", "value_max"),
            "gen_grab": ("value_vec_min", "value_vec_max"),
            "gen_rotate": ("angle_vec_min", "angle_vec_max"),
            "gen_scale": ("scale_vec_min", "scale_vec_max", __syncable),
        },
        "UVSPHERE": {
            "add_circ_verts": ("value_min_int", "value_max_int"),
            "add_sphr_rings": ("value_min_int2", "value_max_int2"),
            "add_radius": ("value_min", "value_max"),
            "gen_grab": ("value_vec_min", "value_vec_max"),
            "gen_rotate": ("angle_vec_min", "angle_vec_max"),
            "gen_scale": ("scale_vec_min", "scale_vec_max", __syncable),
        },
        "ICOSPHERE": {
            "add_sphr_ico": ("value_min_int", "value_max_int"),
            "add_radius": ("value_min", "value_max"),
            "gen_grab": ("value_vec_min", "value_vec_max"),
            "gen_rotate": ("angle_vec_min", "angle_vec_max"),
            "gen_scale": ("scale_vec_min", "scale_vec_max", __syncable),
        },
        "CYLINDER": {
            "add_circ_verts": ("value_min_int", "value_max_int"),
            "add_radius": ("value_min", "value_max"),
            "add_radius2": ("value_min2", "value_max2"),
            "gen_grab": ("value_vec_min", "value_vec_max"),
            "gen_rotate": ("angle_vec_min", "angle_vec_max"),
            "gen_scale": ("scale_vec_min", "scale_vec_max", __syncable),
        },
        "CONE": {
            "add_circ_verts": ("value_min_int", "value_max_int"),
            "add_radius": ("value_min", "value_max"),
            "gen_ins_thick": ("value_min2", "value_max2"),
            "add_sphr_ico": ("value_min3", "value_max3"),
            "gen_grab": ("value_vec_min", "value_vec_max"),
            "gen_rotate": ("angle_vec_min", "angle_vec_max"),
            "gen_scale": ("scale_vec_min", "scale_vec_max", __syncable),
        },
        "TORUS": {
            "add_tor_seg_maj": ("value_min_int", "value_max_int"),
            "add_tor_seg_min": ("value_min_int2", "value_max_int2"),
            "add_tor_rad_maj": ("value_min", "value_max"),
            "add_tor_rad_min": ("value_min2", "value_max2"),
            "add_tor_rad_abso_maj": ("value_min", "value_max"),
            "add_tor_rad_abso_min": ("value_min2", "value_max2"),
            "gen_grab": ("value_vec_min", "value_vec_max"),
            "gen_rotate": ("angle_vec_min", "angle_vec_max"),
        },
        "GRID": {
            "add_grid_x": ("value_min_int", "value_max_int"),
            "add_grid_y": ("value_min_int2", "value_max_int2"),
            "add_size": ("value_min", "value_max"),
            "gen_grab": ("value_vec_min", "value_vec_max"),
            "gen_rotate": ("angle_vec_min", "angle_vec_max"),
            "gen_scale": ("scale_vec_min", "scale_vec_max", __syncable),
        },
        "MONKEY": {
            "add_size": ("value_min", "value_max"),
            "gen_grab": ("value_vec_min", "value_vec_max"),
            "gen_rotate": ("angle_vec_min", "angle_vec_max"),
            "gen_scale": ("scale_vec_min", "scale_vec_max", __syncable),
        },
    },
}
