> # GEN AI Learnings


## test_0002.ipynb

### install rust 
```sh
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

```txt
Rust is installed now. Great!

To get started you may need to restart your current shell.
This would reload your PATH environment variable to include
Cargo's bin directory ($HOME/.cargo/bin).

To configure your current shell, you need to source
the corresponding env file under $HOME/.cargo.
```

source $HOME/.cargo/env


rustc --version

pip install git+https://github.com/huggingface/transformers.git@2ef774211733f0acf8d3415f9284c49ef219e991


## test_0003.ipynb

https://huggingface.co/deepset/roberta-base-squad2

pip install haystack-ai "transformers[torch,sentencepiece]"