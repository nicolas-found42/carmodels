
void FUN_00193000(int param_1,undefined4 *param_2,undefined4 *param_3,undefined4 *param_4,
                 undefined4 *param_5)

{
  int iVar1;
  undefined4 uVar2;
  undefined4 uVar3;
  undefined4 uVar4;
  
  uVar2 = param_2[1];
  uVar3 = param_2[2];
  uVar4 = param_2[3];
  iVar1 = *(int *)(param_1 + 4);
  *(undefined4 *)(iVar1 + 0x100) = *param_2;
  *(undefined4 *)(iVar1 + 0x104) = uVar2;
  *(undefined4 *)(iVar1 + 0x108) = uVar3;
  *(undefined4 *)(iVar1 + 0x10c) = uVar4;
  uVar2 = param_2[1];
  uVar3 = param_2[2];
  uVar4 = param_2[3];
  *(undefined4 *)(iVar1 + 0x110) = *param_2;
  *(undefined4 *)(iVar1 + 0x114) = uVar2;
  *(undefined4 *)(iVar1 + 0x118) = uVar3;
  *(undefined4 *)(iVar1 + 0x11c) = uVar4;
  uVar2 = param_3[1];
  uVar3 = param_3[2];
  uVar4 = param_3[3];
  *(undefined4 *)(iVar1 + 0x120) = *param_3;
  *(undefined4 *)(iVar1 + 0x124) = uVar2;
  *(undefined4 *)(iVar1 + 0x128) = uVar3;
  *(undefined4 *)(iVar1 + 300) = uVar4;
  uVar2 = param_4[1];
  uVar3 = param_4[2];
  uVar4 = param_4[3];
  *(undefined4 *)(iVar1 + 0x130) = *param_4;
  *(undefined4 *)(iVar1 + 0x134) = uVar2;
  *(undefined4 *)(iVar1 + 0x138) = uVar3;
  *(undefined4 *)(iVar1 + 0x13c) = uVar4;
  uVar2 = param_5[1];
  uVar3 = param_5[2];
  uVar4 = param_5[3];
  *(undefined4 *)(iVar1 + 0x140) = *param_5;
  *(undefined4 *)(iVar1 + 0x144) = uVar2;
  *(undefined4 *)(iVar1 + 0x148) = uVar3;
  *(undefined4 *)(iVar1 + 0x14c) = uVar4;
  return;
}

