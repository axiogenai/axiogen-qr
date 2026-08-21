import io
import math
from typing import List, Tuple, Optional, Dict, Any
from PIL import Image, ImageDraw
import qrcode
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H

from .shapes import ModuleShape, EyeShape, draw_module, draw_finder_pattern
from .colors import (
    hex_to_rgba,
    create_linear_gradient,
    create_radial_gradient
)
from .logo_composer import compose_logo_on_qr, LogoPosition
from .exporters import export_png_bytes, export_png_base64, export_svg_string

ERROR_CORRECTION_MAP = {
    'L': ERROR_CORRECT_L,
    'M': ERROR_CORRECT_M,
    'Q': ERROR_CORRECT_Q,
    'H': ERROR_CORRECT_H
}

class QRCodeEngine:
    """
    Production-grade Branded QR Code Generation Engine.
    Supports shapes, gradients, custom eyes, logos, and high-DPI export.
    """

    @staticmethod
    def generate_matrix(data: str, error_correction: str = 'M') -> Tuple[List[List[bool]], int]:
        """Generate binary boolean matrix from payload data."""
        ec_level = ERROR_CORRECTION_MAP.get(error_correction.upper(), ERROR_CORRECT_M)
        qr = qrcode.QRCode(
            version=None,
            error_correction=ec_level,
            box_size=1,
            border=0
        )
        qr.add_data(data)
        qr.make(fit=True)
        return qr.get_matrix(), qr.modules_count

    @staticmethod
    def _is_finder(r: int, c: int, matrix_size: int) -> bool:
        """Check if a coordinate is inside a 7x7 Finder Pattern region."""
        if r < 7 and c < 7:
            return True
        if r < 7 and c >= matrix_size - 7:
            return True
        if r >= matrix_size - 7 and c < 7:
            return True
        return False

    @staticmethod
    def _is_logo_zone(r: int, c: int, matrix_size: int, logo_size_ratio: float = 0.22) -> bool:
        """Check if coordinate is inside the center logo deadzone to prevent ugly module clipping."""
        logo_modules = max(3, int(matrix_size * logo_size_ratio))
        start = (matrix_size - logo_modules) // 2
        end = start + logo_modules
        return start <= r < end and start <= c < end

    @classmethod
    def render_qr(
        cls,
        data: str,
        module_shape: str = ModuleShape.SQUARE,
        eye_shape: str = EyeShape.SQUARE,
        foreground_color: str = "#000000",
        background_color: str = "#FFFFFF",
        eye_color: Optional[str] = None,
        eye_inner_color: Optional[str] = None,
        gradient_stops: Optional[List[Tuple[float, str]]] = None,
        gradient_type: str = "linear",
        gradient_angle: float = 45.0,
        logo_image: Optional[Image.Image] = None,
        logo_position: str = LogoPosition.CENTER,
        logo_size_ratio: float = 0.22,
        module_size: int = 16,
        quiet_zone: int = 4,
        error_correction: str = 'M'
    ) -> Image.Image:
        """
        Renders a fully styled, pixel-perfect PIL Image of the QR code.
        
        Finder patterns are drawn AFTER gradient compositing so the white ring
        and inner dot structure is always preserved.
        
        Logo zone is cleared at the matrix level so modules never awkwardly overlap.
        """
        # Automatically upgrade error correction to 'H' (30%) if logo is present
        if logo_image is not None and error_correction in ('L', 'M'):
            error_correction = 'H'

        matrix, matrix_size = cls.generate_matrix(data, error_correction=error_correction)
        
        total_modules = matrix_size + (quiet_zone * 2)
        total_size = total_modules * module_size

        # Parse Colors
        bg_rgba = hex_to_rgba(background_color)
        fg_rgba = hex_to_rgba(foreground_color)
        eye_outer_rgba = hex_to_rgba(eye_color) if eye_color else fg_rgba
        eye_inner_rgba = hex_to_rgba(eye_inner_color) if eye_inner_color else eye_outer_rgba

        # ──────────────────────────────────────────────
        # STEP 1: Draw ONLY data modules on transparent mask
        #         (Finder patterns and logo deadzone are cleared)
        # ──────────────────────────────────────────────
        data_mask = Image.new("RGBA", (total_size, total_size), (0, 0, 0, 0))
        data_draw = ImageDraw.Draw(data_mask)

        for r in range(matrix_size):
            for c in range(matrix_size):
                if matrix[r][c] and not cls._is_finder(r, c, matrix_size):
                    # Omit modules inside the logo deadzone for clean aesthetic
                    if logo_image is not None and logo_position == LogoPosition.CENTER and cls._is_logo_zone(r, c, matrix_size, logo_size_ratio):
                        continue
                    x = (quiet_zone + c) * module_size
                    y = (quiet_zone + r) * module_size
                    draw_module(data_draw, x, y, module_size, module_shape, fg_rgba)

        # ──────────────────────────────────────────────
        # STEP 2: Compose final image with background
        # ──────────────────────────────────────────────
        final_qr = Image.new("RGBA", (total_size, total_size), bg_rgba)

        if gradient_stops and len(gradient_stops) >= 2:
            # Create gradient image
            if gradient_type == "radial":
                grad_img = create_radial_gradient(total_size, total_size, gradient_stops)
            else:
                grad_img = create_linear_gradient(total_size, total_size, gradient_stops, angle_deg=gradient_angle)
            
            # Use data module alpha as mask to paste gradient ONLY on data modules
            alpha_mask = data_mask.split()[3]
            final_qr.paste(grad_img, (0, 0), mask=alpha_mask)
        else:
            # No gradient: paste data modules directly
            final_qr.paste(data_mask, (0, 0), mask=data_mask)

        # ──────────────────────────────────────────────
        # STEP 3: Draw Finder Patterns DIRECTLY on final image
        #         This guarantees the 3-layer structure:
        #           Layer 1: Outer border (7x7) — colored
        #           Layer 2: White ring (5x5) — background
        #           Layer 3: Inner dot (3x3) — colored
        #         is ALWAYS preserved regardless of gradients.
        # ──────────────────────────────────────────────
        final_draw = ImageDraw.Draw(final_qr)
        
        # If gradient, sample gradient colors at finder pattern positions for eye coloring
        if gradient_stops and len(gradient_stops) >= 2:
            # Use gradient colors for the eyes too
            grad_ref = grad_img if gradient_stops else None
        else:
            grad_ref = None

        finder_positions = [
            (quiet_zone, quiet_zone),                              # Top-Left
            (quiet_zone, quiet_zone + matrix_size - 7),            # Top-Right  
            (quiet_zone + matrix_size - 7, quiet_zone)             # Bottom-Left
        ]

        for fx, fy in finder_positions:
            px = fx * module_size
            py = fy * module_size

            # If gradient is active and no explicit eye_color, sample gradient at eye center
            if grad_ref and not eye_color:
                center_x = int(px + 3.5 * module_size)
                center_y = int(py + 3.5 * module_size)
                center_x = min(center_x, total_size - 1)
                center_y = min(center_y, total_size - 1)
                sampled_color = grad_ref.getpixel((center_x, center_y))
                if len(sampled_color) == 3:
                    sampled_color = sampled_color + (255,)
                current_outer = sampled_color
                current_inner = sampled_color
            else:
                current_outer = eye_outer_rgba
                current_inner = eye_inner_rgba

            draw_finder_pattern(
                final_draw,
                px, py,
                7 * module_size,
                eye_shape,
                current_outer,
                current_inner,
                bg_rgba
            )

        # ──────────────────────────────────────────────
        # STEP 4: Compose Logo if provided
        # ──────────────────────────────────────────────
        if logo_image is not None:
            final_qr = compose_logo_on_qr(
                final_qr,
                logo_image,
                position=logo_position,
                logo_size_ratio=logo_size_ratio,
                bg_color=bg_rgba,
                module_size=module_size,
                matrix_size=matrix_size,
                quiet_zone=quiet_zone
            )

        return final_qr

    @classmethod
    def render_svg(
        cls,
        data: str,
        module_shape: str = ModuleShape.SQUARE,
        eye_shape: str = EyeShape.SQUARE,
        foreground_color: str = "#000000",
        background_color: str = "#FFFFFF",
        gradient_stops: Optional[List[Tuple[float, str]]] = None,
        gradient_type: str = "linear",
        gradient_angle: float = 45.0,
        module_size: int = 10,
        quiet_zone: int = 4,
        error_correction: str = 'M'
    ) -> str:
        """Render pure scalable vector SVG XML string."""
        matrix, _ = cls.generate_matrix(data, error_correction=error_correction)
        return export_svg_string(
            matrix=matrix,
            module_size=module_size,
            quiet_zone=quiet_zone,
            shape=module_shape,
            eye_shape=eye_shape,
            foreground_color=foreground_color,
            background_color=background_color,
            gradient_stops=gradient_stops,
            gradient_type=gradient_type,
            gradient_angle=gradient_angle
        )
