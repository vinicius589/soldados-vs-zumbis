"""Compositor OpenGL para o framebuffer 2D de Soldados vs Zumbis.

O Pygame continua responsável por input, áudio, superfícies, textos e lógica.
Este módulo envia o quadro final para uma textura OpenGL e usa um pequeno
shader para correção de cor, contraste, vinheta e iluminação ambiente.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
from typing import Sequence

import pygame


@dataclass(frozen=True)
class RendererInfo:
    vendor: str
    renderer: str
    version: str

    @property
    def label(self) -> str:
        return f"Pygame + PyOpenGL · {self.renderer}"


@dataclass(frozen=True)
class ActorCommand:
    """Uma silhueta articulada que será deformada pela GPU.

    A origem é sempre o contato dos pés/rodas/casco com o cenário. Isso
    impede a animação de alterar a linha lógica do personagem.
    """

    sprite: pygame.Surface
    x: float
    ground_y: float
    width: float
    height: float
    state: str
    elapsed: float
    enemy: bool = False
    vertical_offset: float = 0.0
    alpha: int = 255
    hit_flash: float = 0.0
    progress: float = 0.0
    profile: str = "generic"


class OpenGLPresenter:
    """Apresenta uma ``pygame.Surface`` em um contexto OpenGL 2.1+.

    A importação de PyOpenGL é tardia de propósito: o teste com driver SDL
    ``dummy`` e o modo de compatibilidade conseguem iniciar mesmo em uma
    máquina que ainda não terminou de instalar as dependências gráficas.
    """

    VERTEX_SHADER = """
        #version 120
        varying vec2 v_uv;

        void main() {
            gl_Position = gl_Vertex;
            v_uv = gl_MultiTexCoord0.xy;
        }
    """

    FRAGMENT_SHADER = """
        #version 120
        uniform sampler2D u_frame;
        uniform vec3 u_tint;
        uniform float u_time;
        uniform float u_strength;
        varying vec2 v_uv;

        void main() {
            vec4 source = texture2D(u_frame, v_uv);
            vec2 centered = v_uv - vec2(0.5);
            float distance_from_center = length(centered * vec2(1.0, 0.86));
            float vignette = 1.0 - smoothstep(0.30, 0.78, distance_from_center);
            float breathing_light = 0.995 + sin(u_time * 0.72) * 0.005;
            float fine_scan = 1.0 - (0.006 * u_strength) *
                (0.5 + 0.5 * sin(v_uv.y * 720.0 * 3.14159265));

            vec3 regional_grade = source.rgb * mix(vec3(1.0), u_tint, 0.10 * u_strength);
            regional_grade *= mix(0.90, 1.025, vignette * u_strength);
            regional_grade *= breathing_light * fine_scan;
            regional_grade = mix(regional_grade, smoothstep(vec3(0.0), vec3(1.0), regional_grade), 0.08);
            gl_FragColor = vec4(regional_grade, source.a);
        }
    """

    ACTOR_VERTEX_SHADER = """
        #version 120
        uniform vec2 u_anchor;
        uniform vec2 u_size;
        uniform vec2 u_screen;
        uniform float u_time;
        uniform float u_direction;
        uniform float u_progress;
        uniform int u_state;
        uniform int u_profile;
        varying vec2 v_uv;

        void main() {
            vec2 local = gl_Vertex.xy;
            v_uv = gl_MultiTexCoord0.xy;

            float cycle = sin(u_time * 10.5);
            float pulse = sin(u_time * 17.0);
            float left_side = 1.0 - smoothstep(0.45, 0.55, local.x);
            float right_side = smoothstep(0.45, 0.55, local.x);
            float lower_body = smoothstep(0.50, 0.98, local.y);
            float upper_body = 1.0 - smoothstep(0.42, 0.78, local.y);
            float head = 1.0 - smoothstep(0.24, 0.39, local.y);
            float torso = smoothstep(0.18, 0.31, local.y) *
                (1.0 - smoothstep(0.54, 0.70, local.y));
            float arm_band = smoothstep(0.25, 0.36, local.y) *
                (1.0 - smoothstep(0.64, 0.78, local.y));
            float left_arm = arm_band * (1.0 - smoothstep(0.44, 0.55, local.x));
            float right_arm = arm_band * smoothstep(0.45, 0.56, local.x);
            float leg_band = smoothstep(0.54, 0.68, local.y);
            float left_leg = leg_band * (1.0 - smoothstep(0.43, 0.53, local.x));
            float right_leg = leg_band * smoothstep(0.47, 0.57, local.x);
            vec2 deform = vec2(0.0);
            float scale_x = 1.0;
            float scale_y = 1.0;

            if (u_state == 14) {
                // A folha frame a frame já contém todo o movimento corporal.
                // A GPU preserva escala, alfa e âncora sem deformar duas vezes
                // braços, pernas, armas ou o contato dos pés com o cenário.
            } else if (u_state == 1) {
                float born = clamp(u_time / 0.28, 0.0, 1.0);
                scale_x = 0.72 + born * 0.28;
                scale_y = scale_x;
                deform.y += (1.0 - born) * 0.16;
            } else if (u_state == 2) {
                // Marcha articulada: cada perna troca apoio e cada braço
                // contrabalança o passo oposto. Corredores ampliam a passada;
                // rastejantes usam braços e quadril em vez de pernas falsas.
                float stride = (u_profile == 21) ? 1.38 : 1.0;
                if (u_profile == 22) {
                    deform.x += u_direction * (left_arm * cycle - right_arm * cycle) * 0.075;
                    deform.y -= (left_arm * max(cycle, 0.0) + right_arm * max(-cycle, 0.0)) * 0.050;
                    deform.x += lower_body * u_direction * sin(u_time * 7.0 + local.y * 7.0) * 0.032;
                    scale_y -= lower_body * 0.055;
                } else {
                    deform.x += u_direction * stride * (left_leg * cycle - right_leg * cycle) * 0.074;
                    deform.y -= stride * (left_leg * max(cycle, 0.0) + right_leg * max(-cycle, 0.0)) * 0.046;
                    deform.x += u_direction * stride * (-left_arm * cycle + right_arm * cycle) * 0.040;
                    deform.x -= head * u_direction * cycle * 0.010;
                    deform.y -= torso * abs(cycle) * 0.009;
                }
            } else if (u_state == 3) {
                float action = (u_progress > 0.001) ? u_progress : clamp(u_time / 0.28, 0.0, 1.0);
                float thrust = sin(action * 3.14159265);
                if (u_profile == 6) {
                    // Operador de morteiro: as mãos descem a granada no tubo
                    // antes do pequeno recuo do disparo.
                    float load = sin(clamp(action * 1.38, 0.0, 1.0) * 3.14159265);
                    deform.x += u_direction * (left_arm + right_arm) * load * 0.036;
                    deform.y += (left_arm + right_arm) * load * 0.082;
                    deform.x += torso * u_direction * load * 0.022;
                } else if (u_profile == 30 || u_profile == 34) {
                    // Golpe corporal de chefes pesados: preparação curta e
                    // descida de braços/martelo, distinta da mordida comum.
                    float swing = sin(action * 3.14159265);
                    float descent = smoothstep(0.36, 0.82, action);
                    deform.y -= (left_arm + right_arm) * (1.0 - descent) * swing * 0.105;
                    deform.x -= u_direction * (left_arm + right_arm) * (1.0 - descent) * swing * 0.060;
                    deform.y += (left_arm + right_arm + torso) * descent * swing * 0.090;
                    scale_y -= lower_body * descent * swing * 0.035;
                } else if (u_profile >= 20) {
                    // Mordida/ataque corporal: os dois braços buscam o alvo,
                    // a cabeça acompanha e o quadril continua plantado.
                    deform.x += u_direction * (left_arm + right_arm) * thrust * 0.125;
                    deform.x += u_direction * (head + torso) * thrust * 0.074;
                    deform.y += head * thrust * 0.030;
                    deform.y -= (left_arm + right_arm) * thrust * 0.022;
                    scale_x += thrust * 0.030;
                } else {
                    // Armas de fogo recuam do ombro, não do corpo inteiro.
                    deform.x -= u_direction * (head + torso + arm_band) * thrust * 0.040;
                    deform.y -= arm_band * thrust * 0.022;
                    scale_x += torso * thrust * 0.014;
                }
            } else if (u_state == 4) {
                float impact = sin(clamp(u_time / 0.16, 0.0, 1.0) * 3.14159265);
                deform.x -= u_direction * (head + torso + arm_band) * impact * 0.095;
                deform.y -= head * impact * 0.030;
                deform.x += sin(u_time * 66.0 + local.y * 8.0) * 0.010;
            } else if (u_state == 5) {
                deform.x += sin(u_time * 15.0 + local.y * 8.0) * (0.018 + upper_body * 0.024);
                deform.y += abs(pulse) * upper_body * 0.012;
            } else if (u_state == 6) {
                float energy = abs(pulse);
                deform.y -= upper_body * energy * 0.030;
                scale_x += energy * 0.025;
                scale_y += energy * 0.018;
            } else if (u_state == 7) {
                scale_x += lower_body * 0.055;
                scale_y -= lower_body * 0.050;
                deform.x += upper_body * u_direction * 0.025;
            } else if (u_state == 8) {
                deform.y += lower_body * 0.10;
                deform.x += sin(u_time * 26.0 + local.y * 10.0) * 0.018;
                scale_y -= lower_body * 0.10;
            } else if (u_state == 9) {
                float fall = clamp(u_progress, 0.0, 1.0);
                float angle = -u_direction * fall * 1.05;
                vec2 pivoted = vec2(local.x - 0.5, local.y - 1.0);
                mat2 rotation = mat2(cos(angle), -sin(angle), sin(angle), cos(angle));
                pivoted = rotation * pivoted;
                local = vec2(pivoted.x + 0.5, pivoted.y + 1.0);
                scale_y = 1.0 - fall * 0.22;
                deform.x += u_direction * fall * 0.06;
            } else if (u_state == 10) {
                deform.y -= abs(sin(u_time * 20.0)) * 0.018;
                deform.x += sin(u_time * 11.0 + local.y * 4.0) * 0.006;
            } else if (u_state == 11) {
                // Braçadas alternadas e rolamento de ombros. A última fileira
                // permanece na superfície do canal, como casco/ponto d'água.
                float stroke = sin(u_time * 8.5);
                deform.x += u_direction * (left_arm * stroke - right_arm * stroke) * 0.090;
                deform.y -= (left_arm * max(stroke, 0.0) + right_arm * max(-stroke, 0.0)) * 0.060;
                deform.y += torso * sin(u_time * 8.5 + local.x * 5.0) * 0.022;
                deform.x += head * cos(u_time * 4.25) * 0.018;
                scale_y += torso * sin(u_time * 8.5) * 0.014;
            } else if (u_state == 12) {
                // Quatro tempos reais: abaixar arma, alcançar o cinto, levar
                // o carregador à arma e recuperar a mira. Nada de texto flutuante.
                float action = clamp(u_progress, 0.0, 1.0);
                float reach = smoothstep(0.02, 0.20, action) * (1.0 - smoothstep(0.30, 0.43, action));
                float carry = smoothstep(0.18, 0.46, action) * (1.0 - smoothstep(0.74, 0.88, action));
                float insert = smoothstep(0.48, 0.66, action) * (1.0 - smoothstep(0.84, 0.98, action));
                deform.x -= right_arm * u_direction * reach * 0.080;
                deform.y += right_arm * reach * 0.105;
                deform.x += right_arm * u_direction * carry * 0.060;
                deform.y -= right_arm * carry * 0.074;
                deform.x += left_arm * u_direction * insert * 0.038;
                deform.y += left_arm * insert * 0.035;
                deform.x += torso * u_direction * (reach - insert) * 0.024;
                deform.y += torso * (reach + carry) * 0.022;
            } else if (u_state == 13) {
                // Habilidades têm silhueta própria por arquétipo de chefe.
                float action = (u_progress > 0.001) ? u_progress : clamp(u_time / 0.46, 0.0, 1.0);
                float power = sin(action * 3.14159265);
                if (u_profile == 30 || u_profile == 34) {
                    // Martelo/colosso: arma e braços sobem, depois esmagam o chão.
                    float windup = 1.0 - smoothstep(0.34, 0.64, action);
                    float slam = smoothstep(0.42, 0.76, action);
                    deform.y -= (left_arm + right_arm) * windup * 0.125;
                    deform.x -= u_direction * (left_arm + right_arm) * windup * 0.065;
                    deform.y += (head + torso + arm_band) * slam * 0.090;
                    scale_y -= lower_body * slam * 0.055;
                    scale_x += lower_body * slam * 0.045;
                } else if (u_profile == 31) {
                    // Comandante: braços abertos/erguidos para ordenar a horda.
                    deform.x += u_direction * (right_arm - left_arm) * power * 0.105;
                    deform.y -= (left_arm + right_arm) * power * 0.100;
                    deform.y -= head * power * 0.025;
                } else if (u_profile == 32 || u_profile == 33) {
                    // Tóxico/necromante: mãos convergem e projetam a energia.
                    deform.x += u_direction * (left_arm + right_arm) * power * 0.105;
                    deform.y -= (left_arm + right_arm) * power * 0.070;
                    scale_x += torso * power * 0.035;
                    scale_y += torso * power * 0.025;
                } else if (u_profile == 35 || u_profile == 36) {
                    // Chefes marinhos emergem, arqueiam o corpo e golpeiam a água.
                    deform.y -= (head + torso) * power * 0.080;
                    deform.x += u_direction * upper_body * power * 0.075;
                    deform.y += lower_body * sin(action * 6.2831853) * 0.030;
                } else {
                    deform.y -= (head + torso + arm_band) * power * 0.055;
                    deform.x += u_direction * (left_arm + right_arm) * power * 0.060;
                }
            } else {
                deform.y -= abs(sin(u_time * 4.8)) * 0.004;
            }

            // Fora da queda, a última fileira da malha é uma âncora física:
            // pés, rodas e casco não podem flutuar por causa da pose.
            if (u_state != 9) {
                float ground_lock = 1.0 - smoothstep(0.88, 1.0, local.y);
                deform *= ground_lock;
            }

            vec2 centered = vec2((local.x - 0.5) * scale_x, (local.y - 1.0) * scale_y);
            vec2 pixel = u_anchor + (centered + deform) * u_size;
            vec2 clip = vec2(pixel.x / u_screen.x * 2.0 - 1.0, 1.0 - pixel.y / u_screen.y * 2.0);
            gl_Position = vec4(clip, 0.0, 1.0);
        }
    """

    ACTOR_FRAGMENT_SHADER = """
        #version 120
        uniform sampler2D u_sprite;
        uniform float u_alpha;
        uniform float u_flash;
        varying vec2 v_uv;

        void main() {
            vec4 color = texture2D(u_sprite, v_uv);
            if (color.a < 0.015) discard;
            color.rgb = mix(color.rgb, vec3(1.0, 0.90, 0.72), clamp(u_flash, 0.0, 1.0));
            color.a *= u_alpha;
            gl_FragColor = color;
        }
    """

    OVERLAY_FRAGMENT_SHADER = """
        #version 120
        uniform sampler2D u_overlay;
        varying vec2 v_uv;

        void main() {
            gl_FragColor = texture2D(u_overlay, v_uv);
        }
    """

    STATE_CODES = {
        "spawn": 1,
        "walk": 2,
        "attack": 3,
        "hit": 4,
        "stunned": 5,
        "support": 6,
        "promote": 6,
        "skill": 13,
        "jump": 7,
        "dig_enter": 8,
        "dig_tunnel": 8,
        "dig_emerge": 8,
        "dead": 9,
        "roll": 10,
        "swim": 11,
        "reload": 12,
        "sprite_sequence": 14,
    }

    PROFILE_CODES = {
        "generic": 0,
        "humanoid": 1,
        "rifle": 2,
        "shotgun": 3,
        "sniper": 4,
        "grenade": 5,
        "mortar": 6,
        "flame": 7,
        "poison": 8,
        "waterjet": 9,
        "radio": 10,
        "promoter": 12,
        "barrier": 13,
        "mine": 14,
        "boat": 15,
        "sub": 16,
        "sprite_sequence": 99,
        "walker": 20,
        "runner": 21,
        "crawler": 22,
        "jumper": 23,
        "digger": 24,
        "shooter": 25,
        "caster": 26,
        "heavy": 27,
        "hammer_boss": 30,
        "commander_boss": 31,
        "toxic_boss": 32,
        "necromancer_boss": 33,
        "colossus_boss": 34,
        "sea_boss": 35,
        "leviathan_boss": 36,
    }

    def __init__(self, width: int, height: int) -> None:
        from OpenGL import GL

        self.gl = GL
        self.width = int(width)
        self.height = int(height)
        self.frame_texture = 0
        self.overlay_texture = 0
        self.sprite_textures: dict[tuple[int, int, int], int] = {}
        self.program = 0
        self.actor_program = 0
        self.overlay_program = 0
        self.actor_vbo = 0
        self.actor_ebo = 0
        self.actor_index_count = 0
        self.closed = False

        self.program = self._link_program(self.VERTEX_SHADER, self.FRAGMENT_SHADER)
        self.actor_program = self._link_program(self.ACTOR_VERTEX_SHADER, self.ACTOR_FRAGMENT_SHADER)
        self.overlay_program = self._link_program(self.VERTEX_SHADER, self.OVERLAY_FRAGMENT_SHADER)
        self.frame_texture = self._make_texture(self.width, self.height)
        self.overlay_texture = self._make_texture(self.width, self.height)
        self._make_actor_mesh(columns=12, rows=14)
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glDisable(GL.GL_CULL_FACE)
        GL.glViewport(0, 0, self.width, self.height)

        self.uniform_frame = GL.glGetUniformLocation(self.program, "u_frame")
        self.uniform_tint = GL.glGetUniformLocation(self.program, "u_tint")
        self.uniform_time = GL.glGetUniformLocation(self.program, "u_time")
        self.uniform_strength = GL.glGetUniformLocation(self.program, "u_strength")
        self.uniform_overlay = GL.glGetUniformLocation(self.overlay_program, "u_overlay")
        self.actor_uniforms = {
            name: GL.glGetUniformLocation(self.actor_program, name)
            for name in (
                "u_anchor",
                "u_size",
                "u_screen",
                "u_time",
                "u_direction",
                "u_progress",
                "u_state",
                "u_profile",
                "u_sprite",
                "u_alpha",
                "u_flash",
            )
        }

        def decoded(token: int) -> str:
            value = GL.glGetString(token)
            return value.decode("utf-8", "replace") if value else "desconhecido"

        self.info = RendererInfo(
            decoded(GL.GL_VENDOR),
            decoded(GL.GL_RENDERER),
            decoded(GL.GL_VERSION),
        )

    def _make_actor_mesh(self, *, columns: int, rows: int) -> None:
        """Envia uma malha compartilhada à GPU uma única vez na abertura."""
        import numpy

        GL = self.gl
        vertices: list[float] = []
        for row in range(rows + 1):
            y = row / rows
            for column in range(columns + 1):
                x = column / columns
                vertices.extend((x, y, x, y))
        indices: list[int] = []
        stride = columns + 1
        for row in range(rows):
            for column in range(columns):
                top_left = row * stride + column
                top_right = top_left + 1
                bottom_left = top_left + stride
                bottom_right = bottom_left + 1
                indices.extend((top_left, top_right, bottom_right, top_left, bottom_right, bottom_left))

        vertex_data = numpy.asarray(vertices, dtype=numpy.float32)
        index_data = numpy.asarray(indices, dtype=numpy.uint16)
        self.actor_vbo = int(GL.glGenBuffers(1))
        self.actor_ebo = int(GL.glGenBuffers(1))
        self.actor_index_count = int(index_data.size)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.actor_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, vertex_data.nbytes, vertex_data, GL.GL_STATIC_DRAW)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.actor_ebo)
        GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, index_data.nbytes, index_data, GL.GL_STATIC_DRAW)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)

    def _make_texture(self, width: int, height: int, pixels: bytes | None = None) -> int:
        """Cria uma textura RGBA com filtragem suave e bordas estáveis."""
        GL = self.gl
        texture = int(GL.glGenTextures(1))
        GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
        GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
        GL.glTexImage2D(
            GL.GL_TEXTURE_2D,
            0,
            GL.GL_RGBA,
            int(width),
            int(height),
            0,
            GL.GL_RGBA,
            GL.GL_UNSIGNED_BYTE,
            pixels,
        )
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        return texture

    def _upload_surface(self, texture: int, surface: pygame.Surface) -> None:
        """Atualiza uma textura já alocada sem recriá-la a cada quadro."""
        GL = self.gl
        if surface.get_size() != (self.width, self.height):
            raise ValueError(
                f"Superfície {surface.get_size()} incompatível com o compositor "
                f"{(self.width, self.height)}."
            )
        pixels = pygame.image.tobytes(surface, "RGBA", False)
        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
        GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
        GL.glTexSubImage2D(
            GL.GL_TEXTURE_2D,
            0,
            0,
            0,
            self.width,
            self.height,
            GL.GL_RGBA,
            GL.GL_UNSIGNED_BYTE,
            pixels,
        )

    def _sprite_texture(self, sprite: pygame.Surface) -> int:
        """Mantém cada recorte original residente na GPU durante a partida."""
        key = (id(sprite), sprite.get_width(), sprite.get_height())
        cached = self.sprite_textures.get(key)
        if cached:
            return cached
        pixels = pygame.image.tobytes(sprite, "RGBA", False)
        texture = self._make_texture(sprite.get_width(), sprite.get_height(), pixels)
        self.sprite_textures[key] = texture
        return texture

    def preload_sprites(self, sprites: Sequence[pygame.Surface]) -> None:
        """Aquece texturas durante a tela de carregamento, nunca numa onda."""
        if self.closed:
            return
        for sprite in sprites:
            if sprite.get_width() > 1 and sprite.get_height() > 1:
                self._sprite_texture(sprite)

    def _compile_shader(self, source: str, shader_type: int) -> int:
        GL = self.gl
        shader = int(GL.glCreateShader(shader_type))
        GL.glShaderSource(shader, source)
        GL.glCompileShader(shader)
        if not GL.glGetShaderiv(shader, GL.GL_COMPILE_STATUS):
            log = GL.glGetShaderInfoLog(shader)
            GL.glDeleteShader(shader)
            if isinstance(log, bytes):
                log = log.decode("utf-8", "replace")
            raise RuntimeError(f"Falha ao compilar shader OpenGL: {log}")
        return shader

    def _link_program(self, vertex_source: str, fragment_source: str) -> int:
        GL = self.gl
        vertex = self._compile_shader(vertex_source, GL.GL_VERTEX_SHADER)
        fragment = self._compile_shader(fragment_source, GL.GL_FRAGMENT_SHADER)
        program = int(GL.glCreateProgram())
        try:
            GL.glAttachShader(program, vertex)
            GL.glAttachShader(program, fragment)
            GL.glLinkProgram(program)
            if not GL.glGetProgramiv(program, GL.GL_LINK_STATUS):
                log = GL.glGetProgramInfoLog(program)
                if isinstance(log, bytes):
                    log = log.decode("utf-8", "replace")
                raise RuntimeError(f"Falha ao ligar shader OpenGL: {log}")
            return program
        except Exception:
            GL.glDeleteProgram(program)
            raise
        finally:
            GL.glDeleteShader(vertex)
            GL.glDeleteShader(fragment)

    def _draw_fullscreen(self, texture: int, *, overlay: bool) -> None:
        """Desenha uma textura cobrindo a janela sem alterar sua orientação."""
        GL = self.gl
        if overlay:
            GL.glUseProgram(self.overlay_program)
            GL.glUniform1i(self.uniform_overlay, 0)
            GL.glEnable(GL.GL_BLEND)
            GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        else:
            GL.glUseProgram(self.program)
            GL.glDisable(GL.GL_BLEND)
        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
        GL.glBegin(GL.GL_QUADS)
        GL.glTexCoord2f(0.0, 0.0)
        GL.glVertex2f(-1.0, 1.0)
        GL.glTexCoord2f(1.0, 0.0)
        GL.glVertex2f(1.0, 1.0)
        GL.glTexCoord2f(1.0, 1.0)
        GL.glVertex2f(1.0, -1.0)
        GL.glTexCoord2f(0.0, 1.0)
        GL.glVertex2f(-1.0, -1.0)
        GL.glEnd()

    def _draw_actor(self, command: ActorCommand) -> None:
        """Deforma uma malha subdividida, preservando seu ponto de contato.

        A subdivisão permite que pernas/rodas, tronco e cabeça reajam em ritmos
        diferentes. Não é um simples ``blit`` deslocado: cada vértice é
        recalculado pelo shader para o estado semântico atual.
        """
        if command.sprite.get_width() <= 1 or command.alpha <= 0:
            return
        GL = self.gl
        texture = self._sprite_texture(command.sprite)
        uniforms = self.actor_uniforms
        GL.glUseProgram(self.actor_program)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
        GL.glUniform1i(uniforms["u_sprite"], 0)
        GL.glUniform2f(
            uniforms["u_anchor"],
            float(command.x),
            float(command.ground_y + command.vertical_offset),
        )
        GL.glUniform2f(uniforms["u_size"], max(1.0, command.width), max(1.0, command.height))
        GL.glUniform2f(uniforms["u_screen"], float(self.width), float(self.height))
        GL.glUniform1f(uniforms["u_time"], max(0.0, float(command.elapsed)))
        GL.glUniform1f(uniforms["u_direction"], -1.0 if command.enemy else 1.0)
        GL.glUniform1f(uniforms["u_progress"], max(0.0, min(1.0, float(command.progress))))
        GL.glUniform1i(uniforms["u_state"], self.STATE_CODES.get(command.state, 0))
        GL.glUniform1i(uniforms["u_profile"], self.PROFILE_CODES.get(command.profile, 0))
        GL.glUniform1f(uniforms["u_alpha"], max(0.0, min(1.0, command.alpha / 255.0)))
        GL.glUniform1f(uniforms["u_flash"], max(0.0, min(1.0, command.hit_flash / 0.13)))

        GL.glDrawElements(
            GL.GL_TRIANGLES,
            self.actor_index_count,
            GL.GL_UNSIGNED_SHORT,
            ctypes.c_void_p(0),
        )

    def _begin_actor_batch(self) -> None:
        """Liga os dois buffers uma vez para todos os atores deste quadro."""
        GL = self.gl
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.actor_vbo)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.actor_ebo)
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glEnableClientState(GL.GL_TEXTURE_COORD_ARRAY)
        GL.glVertexPointer(2, GL.GL_FLOAT, 16, ctypes.c_void_p(0))
        GL.glTexCoordPointer(2, GL.GL_FLOAT, 16, ctypes.c_void_p(8))

    def _end_actor_batch(self) -> None:
        GL = self.gl
        GL.glDisableClientState(GL.GL_TEXTURE_COORD_ARRAY)
        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)

    def present(
        self,
        frame: pygame.Surface,
        *,
        actors: Sequence[ActorCommand] = (),
        overlay: pygame.Surface | None = None,
        elapsed: float,
        tint: tuple[int, int, int],
        strength: float = 1.0,
    ) -> None:
        """Compõe cenário, atores articulados e HUD em três passos de GPU."""
        if self.closed:
            return
        GL = self.gl
        GL.glClearColor(0.015, 0.02, 0.025, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        self._upload_surface(self.frame_texture, frame)
        GL.glUseProgram(self.program)
        GL.glUniform1i(self.uniform_frame, 0)
        GL.glUniform3f(self.uniform_tint, *(channel / 255.0 for channel in tint))
        GL.glUniform1f(self.uniform_time, float(elapsed))
        GL.glUniform1f(self.uniform_strength, max(0.0, min(1.0, float(strength))))
        self._draw_fullscreen(self.frame_texture, overlay=False)

        if actors:
            self._begin_actor_batch()
            try:
                for command in sorted(actors, key=lambda actor: (actor.ground_y + actor.vertical_offset, actor.x)):
                    self._draw_actor(command)
            finally:
                self._end_actor_batch()

        if overlay is not None:
            self._upload_surface(self.overlay_texture, overlay)
            self._draw_fullscreen(self.overlay_texture, overlay=True)

        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        GL.glDisable(GL.GL_BLEND)
        GL.glUseProgram(0)
        pygame.display.flip()

    def close(self) -> None:
        """Libera os objetos da GPU antes de encerrar o contexto SDL."""
        if self.closed:
            return
        self.closed = True
        GL = self.gl
        textures = [self.frame_texture, self.overlay_texture, *self.sprite_textures.values()]
        textures = [int(texture) for texture in textures if texture]
        if textures:
            GL.glDeleteTextures(textures)
        self.frame_texture = 0
        self.overlay_texture = 0
        self.sprite_textures.clear()
        if self.program:
            GL.glDeleteProgram(self.program)
            self.program = 0
        if self.actor_program:
            GL.glDeleteProgram(self.actor_program)
            self.actor_program = 0
        if self.overlay_program:
            GL.glDeleteProgram(self.overlay_program)
            self.overlay_program = 0
        buffers = [buffer for buffer in (self.actor_vbo, self.actor_ebo) if buffer]
        if buffers:
            GL.glDeleteBuffers(len(buffers), buffers)
        self.actor_vbo = 0
        self.actor_ebo = 0
        self.actor_index_count = 0
