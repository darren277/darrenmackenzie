// constants
const BG_COLOR = "black";
const CUBE_COLOR = "green";
const SPEED_X = 0.05; // rps
const SPEED_Y = 0.15; // rps
const SPEED_Z = 0.1; // rps

const SPEED_C = 1;

const POINT3D = function(x, y, z) {
    this.x = x;
    this.y = y;
    this.z = z;
};

let canvas = document.getElementsByTagName('canvas')[0];
var ctx = canvas.getContext("2d");

// dimensions
var h = parseInt(canvas.clientHeight);
var w = parseInt(canvas.clientWidth);

canvas.height = h;
canvas.width = w;

// colours and lines
ctx.fillStyle = BG_COLOR;
ctx.strokeStyle = CUBE_COLOR;
ctx.lineWidth = w / 20;
ctx.lineCap = "round";

// cube parameters
var cx = w / 10;
var cy = h / 10;
var cz = 0;
var size = h / 50;
var vertices = [new POINT3D(cx - size, cy - size, cz - size), new POINT3D(cx + size, cy - size, cz - size), new POINT3D(cx + size, cy + size, cz - size), new POINT3D(cx - size, cy + size, cz - size), new POINT3D(cx - size, cy - size, cz + size), new POINT3D(cx + size, cy - size, cz + size), new POINT3D(cx + size, cy + size, cz + size), new POINT3D(cx - size, cy + size, cz + size)];
var edges = [
    [0, 1],
    [1, 2],
    [2, 3],
    [3, 0], // back face
    [4, 5],
    [5, 6],
    [6, 7],
    [7, 4], // front face
    [0, 4],
    [1, 5],
    [2, 6],
    [3, 7] // connecting sides
];

// set up the animation loop
var timeDelta, timeLast = 0;

let shift_index = 1;
let i = 0;

let reverse = false;
var colorCycleDelta = 0;

let start;

requestAnimationFrame(loop);

function setCharAt(str, index, chr) {
    if (index > str.length - 1) return str;
    return str.substring(0, index) + chr + str.substring(index + 1);
}

function loop(timeNow) {

    // calculate the time difference
    timeDelta = timeNow - timeLast;
    timeLast = timeNow;

    // background
    ctx.fillRect(0, 0, w, h);

    // CYCLE COLORS...
    if (start === undefined || start < 100) {
        start = timeNow;
    };
    colorCycleDelta = timeNow - start;
    if (colorCycleDelta > 100) {
        start = 0;
        if (reverse) {
            if (i < 0) {
                shift_index++;
            };
        } else {
            if (i > 9) {
                shift_index++;
            };
        };
        if (shift_index === 6 && i === 9) {
            shift_index = 1;
        };
        i = parseInt(ctx.strokeStyle[shift_index]);
        if (reverse) {
            i--;
        } else {
            i++;
        };
        var new_i = (i).toString();
        ctx.strokeStyle = setCharAt(ctx.strokeStyle, shift_index, new_i);
        if (ctx.strokeStyle === '#999999') {
            if (reverse === false && shift_index === 6) {
                reverse = true;
                shift_index = 1;
            }

        };
        if (ctx.strokeStyle === '#000000') {
            if (reverse === true && shift_index === 6) {
                reverse = false;
                shift_index = 1;
            }
        };
    }



    // some kind of orbit lol wtf?
    for (let v of vertices) {
        v.x += 0.1;
        v.y += 0.1;
        v.z += 0.1;
    }



    // rotate the cube along the z axis
    let angle = timeDelta * 0.001 * SPEED_Z * Math.PI * 2;
    for (let v of vertices) {
        let dx = v.x - cx;
        let dy = v.y - cy;
        let x = dx * Math.cos(angle) - dy * Math.sin(angle);
        let y = dx * Math.sin(angle) + dy * Math.cos(angle);
        v.x = x + cx;
        v.y = y + cy;
    }

    // rotate the cube along the x axis
    angle = timeDelta * 0.001 * SPEED_X * Math.PI * 2;
    for (let v of vertices) {
        let dy = v.y - cy;
        let dz = v.z - cz;
        let y = dy * Math.cos(angle) - dz * Math.sin(angle);
        let z = dy * Math.sin(angle) + dz * Math.cos(angle);
        v.y = y + cy;
        v.z = z + cz;
    }

    // rotate the cube along the y axis
    angle = timeDelta * 0.001 * SPEED_Y * Math.PI * 2;
    for (let v of vertices) {
        let dx = v.x - cx;
        let dz = v.z - cz;
        let x = dz * Math.sin(angle) + dx * Math.cos(angle);
        let z = dz * Math.cos(angle) - dx * Math.sin(angle);
        v.x = x + cx;
        v.z = z + cz;
    }

    // draw each edge
    for (let edge of edges) {
        ctx.beginPath();
        ctx.moveTo(vertices[edge[0]].x, vertices[edge[0]].y);
        ctx.lineTo(vertices[edge[1]].x, vertices[edge[1]].y);
        ctx.stroke();
    }

    // call the next frame
    requestAnimationFrame(loop);
}</script>
<script>let subscribe_button = document.getElementById('contactbutton');
subscribe_button.style['box-shadow'] = "0px 0px 5px #000, 0px 0px 0px #858585";

let hero_contact_form = document.getElementById('herocontactform');
let footer_contact_form = document.getElementById('footercontactform');

hero_contact_form.style['box-shadow'] = "0px 0px 5px #000, 0px 0px 0px #858585";
footer_contact_form.style['box-shadow'] = "0px 0px 5px #000, 0px 0px 0px #858585";

// clientHeight: 38, clientLeft: 3, clientTop: 3, clientWidth: 127
// offsetLeft: 1633, offsetTop: 45

function calculate_box(el, radius) {
    var viewportOffset = el.getBoundingClientRect();
    // these are relative to the viewport, i.e. the window
    var top = viewportOffset.top;
    var left = viewportOffset.left;

    let width = el.clientWidth;
    let height = el.clientHeight;

    let midwidth = width / 2;
    let midheight = height / 2;

    let middle_x = left + midwidth;
    let middle_y = top + midheight;

    let box = [middle_x - midwidth - radius, middle_y - midheight - radius, middle_x + midwidth + radius, middle_y + midheight + radius];

    return box;
};

let hero_box = calculate_box(hero_contact_form, 50);
let footer_box = calculate_box(footer_contact_form, 50);


function calculate_radius(e) {
    // let x, y = e.clientX, e.clientY;
    let x = e.pageX;
    let y = e.pageY;

    // TODO: Definite code smell surrounding repetition here...
    // Abstract this into a function or class.

    if (x > 1500 && y < 200) {
        let val = 30;
        subscribe_button.style['box-shadow'] = "0px 0px 5px #000, 0px 0px " + val.toString() + "px #858585";
    } else {
        let val = 0;
        subscribe_button.style['box-shadow'] = "0px 0px 5px #000, 0px 0px " + val.toString() + "px #858585";
    }

    if (x > hero_box[0] && y > hero_box[1] && x < hero_box[2] && y < hero_box[3]) {
        let val = 30;
        hero_contact_form.style['box-shadow'] = "0px 0px 5px #000, 0px 0px " + val.toString() + "px #858585";
    } else {
        let val = 0;
        hero_contact_form.style['box-shadow'] = "0px 0px 5px #000, 0px 0px " + val.toString() + "px #858585";
    }

    if (x > footer_box[0] && y > footer_box[1] && x < footer_box[2] && y < footer_box[3]) {
        let val = 30;
        footer_contact_form.style['box-shadow'] = "0px 0px 5px #000, 0px 0px " + val.toString() + "px #858585";
    } else {
        let val = 0;
        footer_contact_form.style['box-shadow'] = "0px 0px 5px #000, 0px 0px " + val.toString() + "px #858585";
    }
};


document.addEventListener('mousemove', calculate_radius, {
    passive: true
});
