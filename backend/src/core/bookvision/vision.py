import cv2
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import pandas as pd


# def book_segments(image_path, model, class_filter="book"):
#     """
#     Visualize YOLOv8 segmentation results and crop books:
#       - Cropped images labeled 'Book 1', 'Book 2', ...
#       - Mask-first crop with bounding box fallback if mask empty
#       - Stores box info and crop coordinates
#       - Supports multiple layout sections (max 20 books per section)
#       - Optional mask overlay visualization
#       - Combines all sections into one final image
#     """
#     import cv2
#     import numpy as np
#     from PIL import Image, ImageDraw, ImageFont
#     import matplotlib.pyplot as plt

#     # Load image
#     image = cv2.imread(image_path)
#     if image is None:
#         raise ValueError(f"Cannot load image: {image_path}")
#     image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
#     h, w = image.shape[:2]

#     # Predict with YOLO segmentation model
#     results = model.predict(image_path, conf=0.5, iou=0.5, device='cpu')

#     crops, labels, crop_coordinates, book_infos = [], [], {}, []
#     image_show = image_rgb.copy()
#     book_id = 1

#     for result in results:
#         if result.masks is None:
#             print("No segmentation masks found.")
#             return

#         masks = result.masks.data.cpu().numpy()
#         boxes = result.boxes.xyxy.cpu().numpy()
#         class_ids = result.boxes.cls.cpu().numpy().astype(int)
#         confidences = result.boxes.conf.cpu().numpy()
#         names = model.names

#         for i, mask in enumerate(masks):
#             cls_name = names[class_ids[i]].lower()
#             if class_filter.lower() not in cls_name:
#                 continue

#             x1, y1, x2, y2 = map(int, boxes[i])
#             conf = float(confidences[i])

#             # Draw bounding box for visualization
#             cv2.rectangle(image_show, (x1, y1), (x2, y2), (0, 255, 0), 2)
#             cv2.putText(image_show, f"Book {book_id}", (x1, y1 - 10),
#                         cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

#             # Bounding box crop
#             bbox_crop = image_rgb[y1:y2, x1:x2].copy()

#             # Mask crop
#             mask_resized = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
#             mask_crop = mask_resized[y1:y2, x1:x2]
#             mask_crop = (mask_crop > 0.5).astype(np.uint8)

#             masked_bit = cv2.bitwise_and(bbox_crop, bbox_crop, mask=mask_crop)
#             black_pixels = np.sum(np.all(masked_bit == 0, axis=2))
#             total_pixels = masked_bit.shape[0] * masked_bit.shape[1]

#             # Hybrid crop: mask first, fallback to bbox if mask mostly black
#             if black_pixels / total_pixels > 0.2:
#                 obj_crop = bbox_crop
#             else:
#                 obj_crop = masked_bit

#             crops.append(obj_crop)
#             labels.append(f"Book {book_id}")
#             crop_coordinates[f"Book {book_id}"] = [x1, y1, x2, y2]
#             book_infos.append({"id": book_id, "box": [x1, y1, x2, y2], "conf": conf})
#             book_id += 1

#     if not crops:
#         print("No valid crops found.")
#         return

#     visualize_boxes(image_path, crop_coordinates)

#     # Layout parameters
#     padding = 20
#     font_size = 20
#     label_space = font_size + 10
#     try:
#         font = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
#     except:
#         font = ImageFont.load_default()

#     heights = [c.shape[0] for c in crops]
#     widths = [c.shape[1] for c in crops]
#     tall_ratio = sum([1 for h, w in zip(heights, widths) if h > w]) / len(crops)
#     horizontal_layout = tall_ratio > 0.5

#     aligned_crops = []
#     for crop in crops:
#         h, w = crop.shape[:2]
#         if horizontal_layout and h < w:
#             # Rotate vertical crop to horizontal
#             crop_rotated = cv2.rotate(crop, cv2.ROTATE_90_CLOCKWISE)
#             aligned_crops.append(crop_rotated)
#         elif not horizontal_layout and w < h:
#             # Rotate horizontal crop to vertical
#             crop_rotated = cv2.rotate(crop, cv2.ROTATE_90_CLOCKWISE)
#             aligned_crops.append(crop_rotated)
#         else:
#             aligned_crops.append(crop)

#     # Split crops into sections (still for internal logic)
#     max_split = 25
#     sections = [aligned_crops[i:i+max_split] for i in range(0, len(aligned_crops), max_split)]
#     section_labels = [labels[i:i+max_split] for i in range(0, len(labels), max_split)]
#     final_images = []

#     for sec_idx, (section_crops, section_lbls) in enumerate(zip(sections, section_labels), 1):
#         heights = [c.shape[0] for c in section_crops]
#         widths = [c.shape[1] for c in section_crops]

#         if not horizontal_layout:
#             canvas_width = max(widths) + 2 * padding
#             canvas_height = sum([h + label_space for h in heights]) + padding * (len(section_crops) + 1)
#             final_img = Image.new("RGB", (canvas_width, canvas_height), color=(255, 255, 255))
#             draw = ImageDraw.Draw(final_img)
#             y_offset = padding
#             for i, crop in enumerate(section_crops):
#                 crop_pil = Image.fromarray(crop)
#                 draw.text((padding, y_offset), section_lbls[i], font=font, fill=(0, 0, 0))
#                 y_offset += label_space
#                 final_img.paste(crop_pil, (padding, y_offset))
#                 y_offset += crop_pil.height + padding
#             layout_type = "Vertical"
#         else:
#             canvas_width = sum(widths) + padding * (len(section_crops) + 1)
#             canvas_height = max([h + label_space for h in heights]) + 2 * padding
#             final_img = Image.new("RGB", (canvas_width, canvas_height), color=(255, 255, 255))
#             draw = ImageDraw.Draw(final_img)
#             x_offset = padding
#             for i, crop in enumerate(section_crops):
#                 crop_pil = Image.fromarray(crop)
#                 draw.text((x_offset, padding), section_lbls[i], font=font, fill=(0, 0, 0))
#                 final_img.paste(crop_pil, (x_offset, padding + label_space))
#                 x_offset += crop_pil.width + padding
#             layout_type = "Horizontal"

#         final_images.append(final_img)

#     # --- Combine all sections into one final image ---
#     combined_width = max(img.width for img in final_images)
#     combined_height = sum(img.height for img in final_images) + padding * (len(final_images) + 1)
#     combined_image = Image.new("RGB", (combined_width, combined_height), color=(255, 255, 255))
#     y_offset = padding
#     for img in final_images:
#         combined_image.paste(img, (padding, y_offset))
#         y_offset += img.height + padding

#     plt.figure(figsize=(12, 12))
#     plt.imshow(combined_image)
#     plt.axis("off")
#     plt.title("All Crops Combined")
#     plt.show()

#     return combined_image, crop_coordinates, layout_type

def book_segments(image_path, model, class_filter="book", threshold=0.8, need_visuals = False):
    """
    Visualize YOLOv8 segmentation results and crop books:
      - Cropped images labeled 'Book 1', 'Book 2', ...
      - Mask-first crop with bounding box fallback if mask empty
      - Stores box info and crop coordinates
      - Supports multiple layout sections (max 20 books per section)
      - Optional mask overlay visualization
      - Combines all sections into one final image
    """

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Cannot load image: {image_path}")
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    h, w = image.shape[:2]

    # Predict with YOLO segmentation model
    results = model.predict(image_path, conf=0.5, iou=0.5, device='cpu')

    crops, labels, crop_coordinates, book_infos = [], [], {}, []
    image_show = image_rgb.copy()
    book_id = 1
    # create an overlay for mask visualization
    mask_overlay = image_rgb.copy()

    for result in results:
        if result.masks is None:
            print("No segmentation masks found.")
            return

        masks = result.masks.data.cpu().numpy()
        boxes = result.boxes.xyxy.cpu().numpy()
        class_ids = result.boxes.cls.cpu().numpy().astype(int)
        confidences = result.boxes.conf.cpu().numpy()
        names = model.names

        for i, mask in enumerate(masks):
            cls_name = names[class_ids[i]].lower()
            if class_filter.lower() not in cls_name:
                continue

            x1, y1, x2, y2 = map(int, boxes[i])
            conf = float(confidences[i])

            # Draw bounding box for visualization
            cv2.rectangle(image_show, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(image_show, f"Book {book_id}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
            
            # Visualize mask on overlay
            mask_resized = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
            color = (0, 0, 255)
            mask_bin = (mask_resized > 0.5).astype(np.uint8)
            colored_mask = np.zeros_like(mask_overlay)
            for c in range(3):
                colored_mask[:, :, c] = mask_bin * color[c]
            mask_overlay = cv2.addWeighted(mask_overlay, 1, colored_mask, 0.7, 0)

            # Bounding box crop
            bbox_crop = image_rgb[y1:y2, x1:x2].copy()

            # Mask crop
            mask_uint8 = (mask > 0.5).astype(np.uint8) * 255  # binary mask 0 or 255

            # Crop mask and image
            mask_crop = mask_uint8[y1:y2, x1:x2]

            # Resize mask if needed (only if non-empty)
            if mask_crop.size > 0 and (mask_crop.shape[0] != bbox_crop.shape[0] or mask_crop.shape[1] != bbox_crop.shape[1]):
                mask_crop = cv2.resize(mask_crop, (bbox_crop.shape[1], bbox_crop.shape[0]),
                                       interpolation=cv2.INTER_NEAREST)

            masked_bit = cv2.bitwise_and(bbox_crop, bbox_crop, mask=mask_crop)
            black_pixels = np.sum(np.all(masked_bit == 0, axis=2))
            total_pixels = masked_bit.shape[0] * masked_bit.shape[1]

            # Hybrid crop: mask first, fallback to bbox if mask mostly black
            if black_pixels / total_pixels > threshold:
                obj_crop = bbox_crop
                # print(f"Book {book_id} - crop")
            else:
                obj_crop = masked_bit

            crops.append(obj_crop)
            labels.append(f"Book {book_id}")
            crop_coordinates[f"Book {book_id}"] = [x1, y1, x2, y2]
            book_infos.append({"id": book_id, "box": [x1, y1, x2, y2], "conf": conf})
            book_id += 1

    if not crops:
        print("No valid crops found.")
        return

    if need_visuals:
        bbox_img = visualize_boxes(image_path, crop_coordinates, mask_overlay)

    # Layout parameters
    padding = 20
    font_size = 20
    label_space = font_size + 10
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
    except:
        font = ImageFont.load_default()

    heights = [c.shape[0] for c in crops]
    widths = [c.shape[1] for c in crops]
    tall_ratio = sum([1 for h, w in zip(heights, widths) if h > w]) / len(crops)
    horizontal_layout = tall_ratio > 0.5

    aligned_crops = []
    for crop in crops:
        h, w = crop.shape[:2]
        if horizontal_layout and h < w:
            # Rotate vertical crop to horizontal
            crop_rotated = cv2.rotate(crop, cv2.ROTATE_90_CLOCKWISE)
            aligned_crops.append(crop_rotated)
        elif not horizontal_layout and w < h:
            # Rotate horizontal crop to vertical
            crop_rotated = cv2.rotate(crop, cv2.ROTATE_90_CLOCKWISE)
            aligned_crops.append(crop_rotated)
        else:
            aligned_crops.append(crop)

    # Split crops into sections (still for internal logic)
    # --- Normalize sizes so small books don't appear tiny ---
    TARGET_LONG_SIDE = 500  # adjust if needed

    normalized_crops = []
    for crop in aligned_crops:
        h, w = crop.shape[:2]

        # determine scale based on the longer side
        long_side = max(h, w)
        scale = TARGET_LONG_SIDE / long_side

        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))

        resized = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        normalized_crops.append(resized)

    aligned_crops = normalized_crops

    max_split = 15
    sections = [aligned_crops[i:i+max_split] for i in range(0, len(aligned_crops), max_split)]
    section_labels = [labels[i:i+max_split] for i in range(0, len(labels), max_split)]
    final_images = []

    for _, (section_crops, section_lbls) in enumerate(zip(sections, section_labels), 1):
        heights = [c.shape[0] for c in section_crops]
        widths = [c.shape[1] for c in section_crops]

        if not horizontal_layout:
            canvas_width = max(widths) + 2 * padding
            canvas_height = sum([h + label_space for h in heights]) + padding * (len(section_crops) + 1)
            final_img = Image.new("RGB", (canvas_width, canvas_height), color=(255, 255, 255))
            draw = ImageDraw.Draw(final_img)
            y_offset = padding
            for i, crop in enumerate(section_crops):
                crop_pil = Image.fromarray(crop)
                draw.text((padding, y_offset), section_lbls[i], font=font, fill=(0, 0, 0))
                y_offset += label_space
                final_img.paste(crop_pil, (padding, y_offset))
                y_offset += crop_pil.height + padding
            layout_type = "Vertical"
        else:
            canvas_width = sum(widths) + padding * (len(section_crops) + 1)
            canvas_height = max([h + label_space for h in heights]) + 2 * padding
            final_img = Image.new("RGB", (canvas_width, canvas_height), color=(255, 255, 255))
            draw = ImageDraw.Draw(final_img)
            x_offset = padding
            for i, crop in enumerate(section_crops):
                crop_pil = Image.fromarray(crop)
                draw.text((x_offset, padding), section_lbls[i], font=font, fill=(0, 0, 0))
                final_img.paste(crop_pil, (x_offset, padding + label_space))
                x_offset += crop_pil.width + padding
            layout_type = "Horizontal"

        final_images.append(final_img)

    # --- Combine all sections into one final image ---
    combined_width = max(img.width for img in final_images)
    combined_height = sum(img.height for img in final_images) + padding * (len(final_images) + 1)
    combined_image = Image.new("RGB", (combined_width, combined_height), color=(255, 255, 255))
    y_offset = padding
    for img in final_images:
        combined_image.paste(img, (padding, y_offset))
        y_offset += img.height + padding

    # if need_visuals:
        # plt.figure(figsize=(12, 12))
        # plt.imshow(combined_image)
        # plt.axis("off")
        # plt.title("All Crops Combined")
        # plt.show()

    return combined_image, bbox_img, mask_overlay, crop_coordinates, layout_type
    
def visualize_boxes(image_path: str, crop_coords: dict, mask_overlay= None,save_path=None):
    """
    Visualize bounding boxes with adaptive labels:
    - Vertical boxes → vertical text inside
    - Horizontal boxes → horizontal text above

    Args:
        image_path (str): Path to the main/original image.
        crop_coords (dict): Dictionary like {"Book 1": [x1, y1, x2, y2], ...}.
        save_path (str, optional): Path to save the visualization (optional).

    Returns:
        np.ndarray: Image with bounding boxes drawn.
    """
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Error: cannot load image at {image_path}")
    
    for label, (x1, y1, x2, y2) in crop_coords.items():
        # Draw bounding box
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2, cv2.LINE_AA)

        # Determine orientation
        box_w = x2 - x1
        box_h = y2 - y1
        vertical_box = box_h > box_w * 1.2  # use a threshold to avoid misclassification

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        font_thickness = 1

        if vertical_box:
            # Vertical label inside box from top
            text_color = (0, 0, 255)
            text_size, _ = cv2.getTextSize(label.split(' ')[1], font, font_scale, font_thickness)
            text_w, text_h = text_size

            # Center horizontally inside the box
            box_width = x2 - x1
            x_text = x1 + (box_width - text_w) // 2

            # Top padding inside the box
            y_text = y1 + text_h + 5  # small padding from top

            # Draw background rectangle
            cv2.rectangle(image,
                        (x_text - 2, y_text - text_h - 2),
                        (x_text + text_w + 2, y_text + 2),
                        (255, 255, 255),
                        -1)
            # Draw the label
            cv2.putText(image, label.split(' ')[1], (x_text, y_text),
                        font, font_scale, text_color, font_thickness, cv2.LINE_AA)
        else:
            # --- Horizontal label inside box centered ---
            text_color = (0, 0, 255)
            text_size, _ = cv2.getTextSize(label.split(' ')[1], font, font_scale, font_thickness)
            text_w, text_h = text_size

            # Top Left text inside box
            x_text = x1 + 5 
            y_text = y1 + text_h + 5

            # Draw background rectangle
            cv2.rectangle(image,
                        (x_text - 2, y_text - text_h - 2),
                        (x_text + text_w + 2, y_text + 2),
                        (255, 255, 255),
                        -1)

            cv2.putText(image, label.split(' ')[1], (x_text, y_text), font, font_scale, text_color, font_thickness, cv2.LINE_AA)

    # Convert to RGB for matplotlib
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # # Visualization
    # _, axes = plt.subplots(1, 2, figsize=(18, 10))

    # # Left: segmentation overlay or boxes visualization
    # axes[0].imshow(mask_overlay)
    # axes[0].axis("off")
    # axes[0].set_title("Detected Segments / Overlay")

    # # Right: combined crops layout
    # axes[1].imshow(image_rgb)
    # axes[1].axis("off")
    # axes[1].set_title("Detected Bounding Boxes")

    # plt.tight_layout()
    # plt.show()

    return image_rgb

def book_recommendation(image_path: str, df: pd.DataFrame, save_path=None, dark_alpha: float = 0.7):
    """
    Highlights bounding boxes and displays clean, professional-style labels.
    """
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Cannot load image: {image_path}")
    h, w = image.shape[:2]

    # --- Step 1: Dark overlay ---
    overlay = np.zeros_like(image, dtype=np.uint8)
    mask = np.zeros((h, w), dtype=np.uint8)

    for _, row in df.iterrows():
        cords = row.get("coord")
        if not isinstance(cords, (list, tuple)) or len(cords) != 4:
            continue
        x1, y1, x2, y2 = map(int, cords)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)

    # --- Step 2: Apply spotlight effect ---
    darkened = cv2.addWeighted(image, 1 - dark_alpha, overlay, dark_alpha, 0)
    combined = np.where(mask[..., None] == 255, image, darkened)

    # --- Step 3: Draw bounding boxes + improved labels ---
    for _, row in df.iterrows():
        cords = row.get("coord")
        score = row.get("similarity_score", None)
        if not isinstance(cords, (list, tuple)) or len(cords) != 4:
            continue

        x1, y1, x2, y2 = map(int, cords)

        # Bounding box
        cv2.rectangle(combined, (x1, y1), (x2, y2), (0, 255, 0), 1, cv2.LINE_AA)

        if score is not None:
            label = f"{score:.2f}%"
            font = cv2.FONT_HERSHEY_DUPLEX
            font_scale = 0.6
            font_thickness = 1

            # Text color and background
            label_bg_color = (35, 35, 35)     # Slightly lighter dark gray
            label_text_color = (255, 255, 255)

            # Get text size
            (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, font_thickness)

            # Label position (small offset above box)
            y_label = max(y1 - text_h - 12, 0)  # 12px above the box for spacing
            x_label = x1 + 2  # slight indent for aesthetic balance

            # Rounded background (simulate rounded edges)
            cv2.rectangle(combined,
                        (x_label - 3, y_label - 2),
                        (x_label + text_w + 6, y_label + text_h + 6),
                        label_bg_color,
                        -1,
                        cv2.LINE_AA)

            # Add text on top
            cv2.putText(combined,
                        label,
                        (x_label, y_label + text_h + 1),
                        font,
                        font_scale,
                        label_text_color,
                        font_thickness,
                        cv2.LINE_AA)

    # --- Step 4: Display result ---
    image_rgb = cv2.cvtColor(combined, cv2.COLOR_BGR2RGB)
    
    # plt.figure(figsize=(10, 10))
    # plt.imshow(image_rgb)
    # plt.axis("off")
    # plt.title("Books with Highlighted Matches", fontsize=16, weight="bold")
    # plt.show()

    # final_img = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    # cv2.imwrite('data/images/final_shelf_image.png', final_img)

    return image_rgb



