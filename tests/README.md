# Testes adicionados pela equipe NEMPA

Esta pasta mantém os testes upstream do Boltz. O arquivo
`test_train_checkpoint_loading.py` foi adicionado pela equipe NEMPA neste fork
para validar o carregamento do checkpoint base em camadas LoRA, incluindo a
copia opcional do trunk para `confidence_module`. Ele nao faz parte da
distribuicao upstream de `jwohlwend/boltz`.

`test_trunk_lora_gradients.py` tambem e um teste NEMPA. Ele verifica o backward
dos adapters LoRA no Pairformer com os pesos base congelados e activation
checkpointing habilitado.