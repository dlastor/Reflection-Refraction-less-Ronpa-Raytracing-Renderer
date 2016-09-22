import argparse
import subprocess
import os
import os.path
import inspect
from GLSLJinja import GLSLJinjaLoader

parser = argparse.ArgumentParser(description="Generate multiple images using batchRIshader with particle_DF_with_motion.vert")
parser.add_argument("exe", help="path to the executable file 'batchRIshader'")
args = parser.parse_args()

outputDir   = os.path.abspath(os.getcwd());
outputName  = os.path.splitext(os.path.basename(__file__))[0]
srcDir      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print("srcDir: " + srcDir, flush=True)
batchRIshader = os.path.abspath(args.exe)
shaderDir = os.path.join(srcDir, "shaders")
os.chdir(shaderDir)

loader = GLSLJinjaLoader(os.path.join(srcDir, "anim_script"))
particleTmpl = loader.get_template("particle_DF_with_motion.vert.tmpl")

def render_frame(source, i):
    p = subprocess.Popen(
        [
            batchRIshader,
            "--num_particles",          str(65536 << (13-5)),
            "--num_div_particles",      str(64),
            "--super_sampling_level",   str(0),
            "--num_tile_x",             str(1),
            "--num_tile_y",             str(1),
            "--output",                 os.path.join(outputDir, outputName + "_frm%d.png" % i),
            "--output_w",               str(1920),
            "--output_h",               str(1080),
            "main_shader.frag",
            "-",
            "particle_DF.frag"
        ],
        universal_newlines = True,
        stdin = subprocess.PIPE
        )
    p.communicate(input = source)
    if p.returncode > 0:
    #    print(source[1000:])
        raise Exception()

def get_line_directive():
    return '#line %d "%s"\n' % (inspect.stack()[1][2], inspect.stack()[1][1].replace("\\", "\\\\"))

def render_template(include, time, gbl_time, cross_roundness = 16.0):
    tmpl = loader.get_includable_template_from_string(include)

    d = dict(time = time, gbl_time = gbl_time, tmpl = tmpl, cross_roundness = cross_roundness)
    return particleTmpl.render(d)

def scene_x_slide(time, gbl_time, i):
    code = (
        get_line_directive() +
        """\
        float t = max(1.0 - `time` - (-star_pos.z+0.09)*4.0, 0.0);
        float x0 = (star_pos.x+0.25);
        star_pos.x += pow(t*8., x0*8.0+0.25)*3.0 + t*x0*8.0;
        """
    )
    render_frame(render_template(code, time, gbl_time, 2.0), i)

def scene_suck(time, gbl_time, i):
    code = (
        get_line_directive() +
        """\
        vec3 center = vec3(0.0);
        float nrmdist = length(star_pos - center) / length(DFmin - center);
        float t = clamp(1.0 + nrmdist - `time`, 0.0, 1.0);
        star_pos = (star_pos - center)*pow(t, 4.0) + center;
        """
    )
    render_frame(render_template(code, time, gbl_time, 2.0), i)

def scene_box_stack(time, gbl_time, i):
    code = (
        get_line_directive() +
        """\
            uvec3 blk = uvec3(abs((star_pos - vec3(0.0, ground, 0.0))* 32.0));
            vec3 timing = uintToFloat(Philox4x32(uvec4(blk.xz, 19, 11), uvec2(32743, 410275))).xyz;
        //    float t = max(`time` - timing.y*0.5 - float(blk.y)/16.0, 0.0);
            float t = max(0.3 + timing.y + float(blk.y)/12.0 - `time`, 0.0);
            star_pos.y += t*t*8.0;
        """
    )
    render_frame(render_template(code, time, gbl_time), i)

def scene_plates(time, gbl_time, i):
    code = (
        get_line_directive() +
        """\
        vec3 rnorm = normalize(round(normal));
        float dot = dot(rnorm, star_pos);
        const float dmin = 0.03, dmax = 0.15;
        float d = (abs(dot) - dmin)/(dmax - dmin);
        float t = max(`time` - (1.0 - d), 0.0);
        star_pos += /*normalize(star_pos)*/sign(dot)*rnorm*t*t*2.;
        """
    )
    render_frame(render_template(code, time, gbl_time), i)

def render_anim():
    FPS = 30.0
    scenes = [(scene_x_slide, 2.0), (scene_suck, 2.0), (scene_box_stack, 2.0), (scene_plates, 2.0)]
    #scenes = [(scene_suck, 2.0)]
    nfrm = 0
    for scn in scenes:
        for i in range(int(FPS*scn[1])):
            scn[0](i/FPS, nfrm/FPS, nfrm)
            nfrm += 1

render_anim()
