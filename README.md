# HitTheAwwwBot
 A discord bot written in python that plays a specific soundboard whenever you say "hit the awww button" in vc.

# Technical Information

> [!NOTE]
> This is just a silly joke tool that isn't designed to be customizable or usable, but I won't stop you from trying...

I'm running on Python 3.9.23, If you use a different python version some packages may not be available and pip might not be able to install them.

All the code is located inside the `__main__.py` file. The soundboard it plays can be configured using the `SOUNDBOARD_ID` variable. It uses the `TOKEN` environment variable for the discord bot token.

It uses an [OpenWakeWord](https://github.com/dscripka/openWakeWord) model to detect when the phrase is said. The models are located inside the [./models](./models) directory in the repository. There is a [section on the OpenWakeWord github](https://github.com/dscripka/openWakeWord?tab=readme-ov-file#training-new-models) about training your own models.

> [!WARNING]
> There is a bug in the simple training Google Colab notebook, but [someone has found a workaround](https://github.com/dscripka/openWakeWord/issues/250)