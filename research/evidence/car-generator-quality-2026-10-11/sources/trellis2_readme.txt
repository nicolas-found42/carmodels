Source: https://github.com/microsoft/TRELLIS.2 (fetched 2026-10-11)
TRELLIS.2 is a state-of-the-art large 3D generative model (4B parameters) designed for high-fidelity image-to-3D generation. It leverages a novel "field-free" sparse voxel structure termed O-Voxel to reconstruct and generate arbitrary 3D assets with complex topologies, sharp features, and full PBR materials.
Hardware: An NVIDIA GPU with at least 24GB of memory is necessary. The code has been verified on NVIDIA A100 and H100 GPUs.
(Single CPU): Textured Mesh → O-Voxel < 10s
TRELLIS.2-4B | 4 Billion | 512³ - 1536³
Please refer to the example_texturing.py for an example of how to generate PBR textures for a given 3D shape.
We provide the full training codebase, enabling users to train TRELLIS.2 from scratch or fine-tune it on custom datasets.
Source: https://github.com/microsoft/TRELLIS.2/blob/main/LICENSE: MIT License Copyright (c) Microsoft Corporation.
Source: https://huggingface.co/microsoft/TRELLIS.2-4B: This model is released under the MIT License.
Source: https://github.com/microsoft/TRELLIS.2/blob/main/example_texturing.py: pipeline = Trellis2TexturingPipeline.from_pretrained("microsoft/TRELLIS.2-4B", config_file="texturing_pipeline.json"); pipeline.cuda(); mesh = trimesh.load(...); image = Image.open(...); output = pipeline.run(mesh, image)
