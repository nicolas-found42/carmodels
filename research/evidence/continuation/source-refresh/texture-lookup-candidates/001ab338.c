
undefined4 FUN_001ab338(undefined8 param_1,int param_2,int param_3)

{
  int iVar1;
  int iVar2;
  float fVar3;
  float fVar4;
  undefined4 uVar5;
  undefined4 uVar6;
  float fVar7;
  float fVar8;
  
  uVar5 = 0;
  iVar2 = (int)param_1;
  fVar8 = *(float *)(*(int *)(iVar2 + 4) + 0xec);
  fVar3 = (float)FUN_001ada38();
  if (*(int *)(param_2 + 0x18) != 0) {
    if (*(int *)(param_2 + 0x60) == 0) {
      fVar7 = *(float *)(param_2 + 0x44);
      fVar4 = 1.0;
      fVar8 = fVar7 * fVar7 - fVar8 * fVar8;
      fVar7 = fVar7 - SQRT((float)((int)fVar8 * (uint)(1.0 < fVar8) |
                                  (uint)(1.0 >= fVar8) * 0x3f800000));
      if (*(float *)(param_2 + 0x38) - fVar3 < 0.0) {
        fVar4 = -1.0;
      }
      fVar4 = (float)((int)fVar7 * (uint)(0.0 < fVar7)) * fVar4;
    }
    else {
      fVar8 = fVar8 * 0.5;
      uVar5 = FUN_00114d58(*(float *)(*(int *)(iVar2 + 4) + 0x74) +
                           (float)((int)fVar8 * (uint)(1.0 < fVar8) |
                                  (uint)(1.0 >= fVar8) * 0x3f800000) *
                           *(float *)(iRam00290534 + 0x58));
      iVar1 = FUN_001e0818(uVar5,*(undefined2 *)(*(int *)(iVar2 + 4) + 0x16));
      fVar4 = (*(float *)(*(int *)(iVar2 + 4) + 0x118) + *(float *)(*(int *)(iVar2 + 4) + 0x114)) -
              *(float *)(iVar1 * 4 + *(int *)(iRam00290534 + 0x38));
    }
    *(float *)(param_3 + 0x1c) = fVar4;
    *(undefined4 *)(param_3 + 0x30) = 2;
    uVar5 = 1;
    iVar2 = FUN_001ae3b8();
    iVar2 = *(int *)(iVar2 + 4);
    *(undefined4 *)(param_3 + 0x28) = 1;
    uVar6 = *(undefined4 *)(iVar2 + 0x58);
    *(undefined4 *)(param_3 + 0x34) = 3;
    *(undefined4 *)(param_3 + 0x14) = uVar6;
    *(undefined4 *)(param_3 + 0x2c) = 1;
    FUN_001a3240(param_1,6);
  }
  return uVar5;
}

