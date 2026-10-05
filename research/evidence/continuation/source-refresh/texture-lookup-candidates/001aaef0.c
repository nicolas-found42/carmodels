
undefined8 FUN_001aaef0(undefined8 param_1,undefined8 param_2,undefined8 param_3)

{
  undefined2 uVar1;
  undefined8 uVar2;
  int iVar3;
  int iVar4;
  float fVar5;
  undefined4 uVar6;
  float fVar7;
  float fVar8;
  float fVar9;
  float fVar10;
  float fVar11;
  float fVar12;
  float fVar13;
  
  uVar2 = 0;
  iVar3 = *(int *)((int)param_1 + 4);
  iVar4 = (int)param_2;
  fVar12 = *(float *)(iVar3 + 0xfc);
  fVar9 = *(float *)(iVar3 + 0xec);
  if (*(int *)(iVar4 + 0x18) != 0) {
    fVar10 = *(float *)(iVar4 + 0x30);
    fVar8 = 5.0;
    fVar13 = *(float *)(*(int *)(*(int *)(iVar4 + 0x18) + 4) + 0xec);
    if (0.0 < fVar12) {
      fVar8 = (*(float *)(iVar4 + 0x20) / fVar12) * *(float *)(iVar4 + 0x20) + 5.0;
    }
    if ((5.0 <= fVar10) || (fVar9 <= 5.0)) {
      if (fVar10 < fVar8) {
        fVar11 = 1.0;
        fVar5 = (float)FUN_001ada38(param_1);
        iVar3 = *(int *)((int)param_1 + 4);
        uVar1 = *(undefined2 *)(iVar3 + 0x16);
        uVar6 = FUN_00114d58(*(float *)(iVar3 + 0x74) +
                             (float)((int)fVar9 * (uint)(fVar11 < fVar9) |
                                    (int)fVar11 * (uint)(fVar11 >= fVar9)) *
                             *(float *)(iRam00290534 + 0x58));
        uVar2 = FUN_001e0818(uVar6,uVar1);
        fVar7 = (float)FUN_001e0d90(uVar6,uVar2);
        iVar3 = (int)param_3;
        *(undefined4 *)(iVar3 + 0x30) = 2;
        *(float *)(iVar3 + 0x1c) = fVar5 - fVar7;
        FUN_001ab118(param_1,param_2,param_3);
        fVar8 = fVar8 * 0.5;
        if ((fVar10 < fVar8) || (fVar12 * 0.5 < *(float *)(iVar4 + 0x20))) {
          fVar9 = fVar9 - *(float *)(iVar4 + 0x20) * 1.0999999;
        }
        else {
          fVar12 = 0.0;
          fVar8 = (fVar10 - fVar8) / fVar8;
          if (0.0 <= fVar8) {
            fVar12 = (float)((int)fVar8 * (uint)(fVar8 < fVar11) |
                            (int)fVar11 * (uint)(fVar8 >= fVar11));
          }
          fVar9 = fVar13 + (fVar9 - fVar13) * fVar12;
        }
        *(uint *)(iVar3 + 0x14) = (int)fVar9 * (uint)(0.0 < fVar9);
        *(undefined4 *)(iVar3 + 0x2c) = 7;
        *(undefined4 *)(iVar3 + 0x34) = 3;
        *(undefined4 *)(iVar3 + 0x28) = 1;
        FUN_001a3240(param_1,1);
        uVar2 = 1;
      }
    }
    else {
      uVar2 = FUN_001abfa8();
    }
  }
  return uVar2;
}

