# Hyperparameters:

## random data unlearning 

### CNN Model for MNIST and Fashion-MNIST
LATENT_DIMS = 8

UNLEARNING_EPOCH = 20

UNLEARNING_LR_UE = 0.00005

UNLEARNING_LR_RA = 0.0001

TEMP = 5

### RestNet Model for CIFAR10 and SVHN
LATENT_DIMS = 16

UNLEARNING_EPOCH = 40

UNLEARNING_LR_UE = 0.00001

UNLEARNING_LR_RA = 0.00004

TEMP = 20


## class unlearning 

### CNN Model for MNIST and Fashion-MNIST
LATENT_DIMS = 8

UNLEARNING_EPOCH = 20

UNLEARNING_LR_UE = 0.00005

UNLEARNING_LR_RA = 0.0001

TEMP = 20

### RestNet Model for CIFAR10 and SVHN
LATENT_DIMS = 16

UNLEARNING_EPOCH = 40

UNLEARNING_LR_UE = 0.00001

UNLEARNING_LR_RA = 0.00005

TEMP = 20

## noisy label unlearning 

### CNN Model for MNIST and Fashion-MNIST
LATENT_DIMS = 8

UNLEARNING_EPOCH = 20

UNLEARNING_LR_UE = 0.00005

UNLEARNING_LR_RA = 0.0001

TEMP = 20
### RestNet Model for CIFAR10 and SVHN
LATENT_DIMS = 16

UNLEARNING_EPOCH = 40

UNLEARNING_LR_UE = 0.00001

UNLEARNING_LR_RA = 0.00004

TEMP = 5