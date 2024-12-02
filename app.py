import gradio as gr
# from gradio_litmodel3d import LitModel3D

import os
from typing import *
import imageio
import uuid
from PIL import Image
from trellis.pipelines import TrellisImageTo3DPipeline
from trellis.utils import render_utils, postprocessing_utils


def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Preprocess the input image.

    Args:
        image (Image.Image): The input image.

    Returns:
        Image.Image: The preprocessed image.
    """
    return pipeline.preprocess_image(image)


def image_to_3d(image: Image.Image) -> Tuple[dict, str]:
    """
    Convert an image to a 3D model.

    Args:
        image (Image.Image): The input image.

    Returns:
        dict: The information of the generated 3D model.
        str: The path to the video of the 3D model.
    """
    outputs = pipeline(image, formats=["gaussian", "mesh"], preprocess_image=False)
    video = render_utils.render_video(outputs['gaussian'][0])['color']
    model_id = uuid.uuid4()
    video_path = f"/tmp/Trellis-demo/{model_id}.mp4"
    os.makedirs(os.path.dirname(video_path), exist_ok=True)
    imageio.mimsave(video_path, video, fps=30)
    model = {'gaussian': outputs['gaussian'][0], 'mesh': outputs['mesh'][0], 'model_id': model_id}
    return model, video_path


def extract_glb(model: dict, mesh_simplify: float, texture_size: int) -> Tuple[str, str]:
    """
    Extract a GLB file from the 3D model.

    Args:
        model (dict): The generated 3D model.
        mesh_simplify (float): The mesh simplification factor.
        texture_size (int): The texture resolution.

    Returns:
        str: The path to the extracted GLB file.
    """
    glb = postprocessing_utils.to_glb(model['gaussian'], model['mesh'], simplify=mesh_simplify, texture_size=texture_size)
    glb_path = f"/tmp/Trellis-demo/{model['model_id']}.glb"
    glb.export(glb_path)
    return glb_path, glb_path


def activate_button() -> gr.Button:
    return gr.Button(interactive=True)


def deactivate_button() -> gr.Button:
    return gr.Button(interactive=False)


with gr.Blocks() as demo:
    with gr.Row():
        with gr.Column():
            image_prompt = gr.Image(label="Image Prompt", image_mode="RGBA", type="pil", height=300)
            generate_btn = gr.Button("Generate", interactive=False)

            mesh_simplify = gr.Slider(0.9, 0.98, label="Simplify", value=0.95, step=0.01)
            texture_size = gr.Slider(512, 2048, label="Texture Size", value=1024, step=512)
            extract_glb_btn = gr.Button("Extract GLB", interactive=False)

        with gr.Column():
            video_output = gr.Video(label="Generated 3D Asset", autoplay=True, loop=True, height=300)
            model_output = gr.Model3D(label="Extracted GLB", height=300)
            download_glb = gr.DownloadButton(label="Download GLB", interactive=False)

    # Example images at the bottom of the page
    with gr.Row():
        examples = gr.Examples(
            examples=[
                f'assets/example_image/{image}'
                for image in os.listdir("assets/example_image")
            ],
            inputs=[image_prompt],
            fn=lambda image: (preprocess_image(image), gr.Button(interactive=True)),
            outputs=[image_prompt, generate_btn],
            run_on_click=True,
            examples_per_page=64,
        )

    model = gr.State()

    # Handlers
    image_prompt.upload(
        preprocess_image,
        inputs=[image_prompt],
        outputs=[image_prompt],
    ).then(
        activate_button,
        outputs=[generate_btn],
    )

    image_prompt.clear(
        deactivate_button,
        outputs=[generate_btn],
    )

    generate_btn.click(
        image_to_3d,
        inputs=[image_prompt],
        outputs=[model, video_output],
    ).then(
        activate_button,
        outputs=[extract_glb_btn],
    )

    video_output.clear(
        deactivate_button,
        outputs=[extract_glb_btn],
    )

    extract_glb_btn.click(
        extract_glb,
        inputs=[model, mesh_simplify, texture_size],
        outputs=[model_output, download_glb],
    ).then(
        activate_button,
        outputs=[download_glb],
    )

    model_output.clear(
        deactivate_button,
        outputs=[download_glb],
    )
    

# Launch the Gradio app
if __name__ == "__main__":
    pipeline = TrellisImageTo3DPipeline.from_pretrained("JeffreyXiang/TRELLIS-image-large")
    pipeline.cuda()
    demo.launch()