/**
 * DarkVeil — WebGL animated background for Lumora Dev
 *
 * Self-contained, zero-dependency WebGL 1.0 implementation.
 * Exposes window.DarkVeil for adaptive mode control.
 *
 * Settings (matching the React component props):
 *   hueShift          275   — violet/purple hue (degrees)
 *   noiseIntensity    0.02  — grain overlay strength
 *   scanlineIntensity 0     — disabled
 *   speed             0.35  — base animation speed
 *   scanlineFrequency 4     — unused at intensity 0
 *   warpAmount        1.2   — organic distortion strength
 */
(function () {
  'use strict';

  /* ─── Config ─────────────────────────────────────────────────────── */
  const CFG = {
    hueShift:          275,
    noiseIntensity:    0.02,
    scanlineIntensity: 0,
    speed:             0.35,
    warpAmount:        1.2,
    // Reduced-intensity values used when code viewer is open
    codingSpeed:       0.08,
    codingWarp:        0.4,
    // Transition duration (seconds of lerp)
    transitionDuration: 2.5,
  };

  /* ─── Vertex shader ──────────────────────────────────────────────── */
  const VERT = `
attribute vec2 a_pos;
void main() { gl_Position = vec4(a_pos, 0.0, 1.0); }
`;

  /* ─── Fragment shader ────────────────────────────────────────────── */
  const FRAG = `
precision mediump float;

uniform vec2  u_res;
uniform float u_time;
uniform float u_hue;
uniform float u_noise;
uniform float u_speed;
uniform float u_warp;

/* ── Gradient noise helpers ─────────────────────────────────────── */
vec2 hash2(vec2 p) {
  p = vec2(dot(p, vec2(127.1, 311.7)),
           dot(p, vec2(269.5, 183.3)));
  return -1.0 + 2.0 * fract(sin(p) * 43758.5453);
}

float gnoise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(dot(hash2(i + vec2(0,0)), f - vec2(0,0)),
        dot(hash2(i + vec2(1,0)), f - vec2(1,0)), u.x),
    mix(dot(hash2(i + vec2(0,1)), f - vec2(0,1)),
        dot(hash2(i + vec2(1,1)), f - vec2(1,1)), u.x),
    u.y);
}

/* ── Fractal Brownian Motion ─────────────────────────────────────── */
float fbm(vec2 p) {
  float v = 0.0, a = 0.5;
  mat2 rot = mat2( 0.8776, 0.4794, -0.4794, 0.8776); /* ~28.6 deg */
  for (int i = 0; i < 5; i++) {
    v += a * gnoise(p);
    p  = rot * p * 2.0 + vec2(100.0);
    a *= 0.5;
  }
  return v;
}

/* ── HSL → RGB ───────────────────────────────────────────────────── */
vec3 hsl2rgb(float h, float s, float l) {
  vec3 rgb = clamp(abs(mod(h * 6.0 + vec3(0.0, 4.0, 2.0), 6.0) - 3.0) - 1.0,
                   0.0, 1.0);
  return l + s * (rgb - 0.5) * (1.0 - abs(2.0 * l - 1.0));
}

void main() {
  vec2 uv = gl_FragCoord.xy / u_res;
  float t  = u_time * u_speed;

  /* Double warp: q → r → f gives deep organic layering */
  vec2 p = uv * 2.8;

  vec2 q;
  q.x = fbm(p + t * 0.08);
  q.y = fbm(p + vec2(5.2, 1.3) + t * 0.08);

  vec2 r;
  r.x = fbm(p + u_warp * q + vec2(1.7, 9.2) + t * 0.12);
  r.y = fbm(p + u_warp * q + vec2(8.3, 2.8) + t * 0.12);

  float f = fbm(p + u_warp * r + t * 0.04);

  /* Keep it very dark — matte black with faint violet breathing */
  float brightness = 0.018 + 0.038 * max(f, 0.0);

  float hue = u_hue + 0.04 * (f - 0.5);   /* slight hue drift     */
  float sat  = 0.55 + 0.35 * f;            /* saturation variation */

  vec3 col = hsl2rgb(hue, sat, brightness);

  /* Grain overlay */
  float grain = gnoise(uv * 380.0 + t * 12.0) * u_noise;
  col += grain * 0.012;

  gl_FragColor = vec4(col, 1.0);
}
`;

  /* ─── State ──────────────────────────────────────────────────────── */
  let canvas, gl, prog, buf;
  let uRes, uTime, uHue, uNoise, uSpeed, uWarp;
  let rafId       = null;
  let startTime   = performance.now();
  let paused      = false;
  let pauseOffset = 0;           // accumulated time while paused
  let lastPauseAt = 0;

  // Animated speed / warp (lerped toward target)
  let currentSpeed = CFG.speed;
  let currentWarp  = CFG.warpAmount;
  let targetSpeed  = CFG.speed;
  let targetWarp   = CFG.warpAmount;

  // Pixel ratio (reduced on mobile)
  function dpr() {
    const isMobile = window.matchMedia('(max-width: 768px)').matches;
    return isMobile ? Math.min(window.devicePixelRatio || 1, 1) : Math.min(window.devicePixelRatio || 1, 2);
  }

  /* ─── CSS fallback (headless / no-WebGL environments) ───────────── */
  function initCSSFallback() {
    const el = document.getElementById('darkveil-canvas');
    if (!el) return;

    // Inject keyframe animation once
    if (!document.getElementById('dv-fallback-style')) {
      const s = document.createElement('style');
      s.id = 'dv-fallback-style';
      s.textContent = `
        @keyframes dv-breathe {
          0%   { background-position: 0% 0%;   opacity: 0.85; }
          33%  { background-position: 60% 40%; opacity: 1;    }
          66%  { background-position: 100% 60%;opacity: 0.90; }
          100% { background-position: 0% 0%;   opacity: 0.85; }
        }
        @keyframes dv-pulse {
          0%,100% { opacity: 0.7; }
          50%     { opacity: 1;   }
        }
        @media (prefers-reduced-motion: reduce) {
          #darkveil-canvas { animation: none !important; }
        }
      `;
      document.head.appendChild(s);
    }

    // Apply a dark animated gradient that echoes the shader palette
    el.style.cssText = `
      position: fixed;
      inset: 0;
      width: 100%;
      height: 100%;
      z-index: 0;
      pointer-events: none;
      user-select: none;
      background:
        radial-gradient(ellipse 80% 60% at 20% 30%,  rgba(76,29,149,0.18) 0%, transparent 65%),
        radial-gradient(ellipse 60% 80% at 80% 70%,  rgba(109,40,217,0.12) 0%, transparent 60%),
        radial-gradient(ellipse 100% 100% at 50% 50%, rgba(15,10,30,1)      0%, #09090b 100%);
      background-size: 300% 300%;
      animation: dv-breathe ${(1 / CFG.speed * 8).toFixed(1)}s ease-in-out infinite;
    `;
  }

  /* ─── WebGL bootstrap ────────────────────────────────────────────── */
  function compileShader(type, src) {
    const s = gl.createShader(type);
    gl.shaderSource(s, src);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
      console.warn('[DarkVeil] Shader error:', gl.getShaderInfoLog(s));
      gl.deleteShader(s);
      return null;
    }
    return s;
  }

  function buildProgram() {
    const vs = compileShader(gl.VERTEX_SHADER,   VERT);
    const fs = compileShader(gl.FRAGMENT_SHADER, FRAG);
    if (!vs || !fs) return null;
    const p = gl.createProgram();
    gl.attachShader(p, vs);
    gl.attachShader(p, fs);
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) {
      console.warn('[DarkVeil] Link error:', gl.getProgramInfoLog(p));
      return null;
    }
    gl.deleteShader(vs);
    gl.deleteShader(fs);
    return p;
  }

  function init() {
    canvas = document.getElementById('darkveil-canvas');
    if (!canvas) { console.warn('[DarkVeil] canvas not found'); return; }

    gl = canvas.getContext('webgl', {
      alpha:                 false,
      antialias:             false,
      depth:                 false,
      stencil:               false,
      powerPreference:       'low-power',
      preserveDrawingBuffer: false,
    });

    if (!gl) {
      initCSSFallback();
      return;
    }

    prog = buildProgram();
    if (!prog) return;

    /* Full-screen triangle (more efficient than two triangles) */
    buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER,
      new Float32Array([-1, -1,  3, -1,  -1, 3]),
      gl.STATIC_DRAW);

    const aPos = gl.getAttribLocation(prog, 'a_pos');
    gl.enableVertexAttribArray(aPos);
    gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);

    gl.useProgram(prog);
    uRes   = gl.getUniformLocation(prog, 'u_res');
    uTime  = gl.getUniformLocation(prog, 'u_time');
    uHue   = gl.getUniformLocation(prog, 'u_hue');
    uNoise = gl.getUniformLocation(prog, 'u_noise');
    uSpeed = gl.getUniformLocation(prog, 'u_speed');
    uWarp  = gl.getUniformLocation(prog, 'u_warp');

    /* Hue in [0..1] from degrees */
    gl.uniform1f(uHue,   CFG.hueShift / 360.0);
    gl.uniform1f(uNoise, CFG.noiseIntensity);

    resize();
    startLoop();
  }

  /* ─── Resize ─────────────────────────────────────────────────────── */
  function resize() {
    if (!canvas || !gl) return;
    const r = dpr();
    const w = Math.floor(window.innerWidth  * r);
    const h = Math.floor(window.innerHeight * r);
    if (canvas.width === w && canvas.height === h) return;
    canvas.width  = w;
    canvas.height = h;
    gl.viewport(0, 0, w, h);
    gl.uniform2f(uRes, w, h);
  }

  /* ─── Render loop ────────────────────────────────────────────────── */
  function lerp(a, b, t) { return a + (b - a) * t; }

  function frame() {
    if (!gl) return;

    /* Smooth lerp toward target speed/warp */
    const lerpRate = 0.025;
    currentSpeed = lerp(currentSpeed, targetSpeed, lerpRate);
    currentWarp  = lerp(currentWarp,  targetWarp,  lerpRate);

    const elapsed = (performance.now() - startTime - pauseOffset) / 1000;

    gl.uniform1f(uTime,  elapsed);
    gl.uniform1f(uSpeed, currentSpeed);
    gl.uniform1f(uWarp,  currentWarp);

    gl.drawArrays(gl.TRIANGLES, 0, 3);
    rafId = requestAnimationFrame(frame);
  }

  function startLoop() {
    if (rafId) return;
    paused = false;
    rafId  = requestAnimationFrame(frame);
  }

  function stopLoop() {
    if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
    paused = true;
  }

  /* ─── Page visibility — pause when tab is hidden ─────────────────── */
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      lastPauseAt = performance.now();
      stopLoop();
    } else {
      pauseOffset += performance.now() - lastPauseAt;
      startLoop();
    }
  });

  /* ─── prefers-reduced-motion ─────────────────────────────────────── */
  const rmq = window.matchMedia('(prefers-reduced-motion: reduce)');
  function applyMotionPreference() {
    if (rmq.matches) {
      /* Freeze animation — draw one static frame then stop */
      stopLoop();
      if (gl) {
        const elapsed = (performance.now() - startTime - pauseOffset) / 1000;
        gl.uniform1f(uTime,  elapsed);
        gl.uniform1f(uSpeed, 0.0);
        gl.uniform1f(uWarp,  0.0);
        gl.drawArrays(gl.TRIANGLES, 0, 3);
      }
    } else {
      if (!paused) startLoop();
    }
  }
  rmq.addEventListener('change', applyMotionPreference);

  /* ─── Resize observer ────────────────────────────────────────────── */
  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(resize, 120);
  });

  /* ─── Public API — window.DarkVeil ───────────────────────────────── */
  window.DarkVeil = {
    /**
     * setMode('chat')   — full animation (default)
     * setMode('coding') — reduced, less distracting
     * setMode('idle')   — nearly paused (future full-screen editor)
     */
    setMode(mode) {
      switch (mode) {
        case 'coding':
          targetSpeed = CFG.codingSpeed;
          targetWarp  = CFG.codingWarp;
          break;
        case 'idle':
          targetSpeed = 0.02;
          targetWarp  = 0.2;
          break;
        case 'chat':
        default:
          targetSpeed = CFG.speed;
          targetWarp  = CFG.warpAmount;
          break;
      }
    },

    /** Force-pause (e.g. future full-screen editor overlay) */
    pause() { stopLoop(); },

    /** Resume */
    resume() { if (!rmq.matches && !document.hidden) startLoop(); },

    /** Dispose all GPU resources */
    destroy() {
      stopLoop();
      if (gl) {
        gl.deleteProgram(prog);
        gl.deleteBuffer(buf);
      }
      prog = buf = gl = null;
    },
  };

  /* ─── Boot after DOM is ready ────────────────────────────────────── */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
    applyMotionPreference();
  }
})();
