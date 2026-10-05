
void FUN_00192948(undefined8 param_1,int param_2)

{
  int iVar1;
  undefined4 uVar2;
  undefined8 uVar3;
  int iVar4;
  
  uVar2 = FUN_00117c58(param_1,0x23b7b0,4);
  *(undefined4 *)(*(int *)(param_2 + 4) + 0xec) = uVar2;
  uVar2 = FUN_00117c58(param_1,0x23b7b0,4);
  *(undefined4 *)(*(int *)(param_2 + 4) + 0xf0) = uVar2;
  uVar2 = FUN_00117c58(param_1,0x23b7b0,4);
  *(undefined4 *)(*(int *)(param_2 + 4) + 0xf4) = uVar2;
  uVar3 = FUN_0010d020(0x30);
  FUN_0020c7fc(uVar3,0,0x30);
  uVar2 = FUN_00117cb8(param_1);
  iVar4 = (int)uVar3;
  *(undefined4 *)(iVar4 + 4) = uVar2;
  uVar2 = FUN_00117cb8(param_1);
  *(undefined4 *)(iVar4 + 0x14) = uVar2;
  uVar2 = FUN_00117cb8(param_1);
  *(undefined4 *)(iVar4 + 0x24) = uVar2;
  uVar2 = FUN_00117cb8(param_1);
  *(undefined4 *)(iVar4 + 8) = uVar2;
  uVar2 = FUN_00117cb8(param_1);
  *(undefined4 *)(iVar4 + 0x18) = uVar2;
  uVar2 = FUN_00117cb8(param_1);
  *(undefined4 *)(iVar4 + 0x28) = uVar2;
  uVar2 = FUN_00117cb8(param_1);
  *(undefined4 *)(iVar4 + 0xc) = uVar2;
  uVar2 = FUN_00117cb8(param_1);
  *(undefined4 *)(iVar4 + 0x1c) = uVar2;
  uVar2 = FUN_00117cb8(param_1);
  iVar1 = *(int *)(param_2 + 4);
  *(undefined4 *)(iVar4 + 0x2c) = uVar2;
  *(int *)(iVar1 + 0x164) = iVar4;
  return;
}

