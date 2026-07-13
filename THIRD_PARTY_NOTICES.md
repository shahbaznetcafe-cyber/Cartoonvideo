# Third-Party Notices

## TalkingHead

SBZ AI Video Studio's character capability model references clearly reusable
concepts and public compatibility names from TalkingHead, including its Mixamo
bone-name normalization, ARKit blend-shape set, Oculus viseme set, and tier
planning for later morph interpolation.

- Project: https://github.com/met4citizen/TalkingHead
- Reference commit: `eed58d198076a7e1e825f804802921c4d3804d46`
- Referenced sources: `README.md` Appendix A and `modules/talkinghead.mjs`
- SBZ adaptation: `threejs_render/facial_runtime.js` uses independently written
  acceleration, velocity-limit, baseline, blink, and gaze logic informed by
  those concepts.

TalkingHead is licensed under the MIT License:

> MIT License
>
> Copyright (c) 2023-2024 Mika Suominen
>
> Permission is hereby granted, free of charge, to any person obtaining a copy
> of this software and associated documentation files (the "Software"), to deal
> in the Software without restriction, including without limitation the rights
> to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
> copies of the Software, and to permit persons to whom the Software is
> furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all
> copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
> IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
> FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
> AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
> LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
> OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
> SOFTWARE.

No TalkingHead avatars, model weights, generated media, language rule tables,
or application/runtime bundle are included in SBZ AI Video Studio.
