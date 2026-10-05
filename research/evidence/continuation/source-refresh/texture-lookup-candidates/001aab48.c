
undefined8 FUN_001aab48(undefined8 param_1,undefined8 param_2,undefined8 param_3)

{
  int iVar1;
  int iVar2;
  undefined8 uVar3;
  int iVar4;
  int iVar5;
  int iVar6;
  int *piVar7;
  long lVar8;
  float fVar9;
  float fVar10;
  float fVar11;
  float fVar12;
  float fVar13;
  
  lVar8 = 0;
  fVar9 = 1.0;
  piVar7 = (int *)param_1;
  iVar2 = piVar7[1];
  iVar6 = (int)param_2;
  fVar13 = *(float *)(iVar2 + 0xec);
  if (*(int *)(iVar6 + 0x18) == 0) {
    return 0;
  }
  if (*(int *)(iVar6 + 100) == 0) {
    iVar2 = *(int *)(iVar6 + 0x60);
  }
  else {
    fVar10 = *(float *)(*(int *)(*(int *)(iVar2 + 0x14c) + 0x174) + 0x50) * 0.5;
    if (0.0 < *(float *)(iVar2 + 0xfc)) {
      fVar10 = (fVar13 * fVar13) / *(float *)(iVar2 + 0xfc) + fVar10;
    }
    else {
      fVar10 = fVar10 + 0.0;
    }
    fVar12 = 5.0;
    if (5.0 <= fVar10) {
      fVar12 = (float)((int)fVar10 * (uint)(fVar10 < 1000.0) | (uint)(fVar10 >= 1000.0) * 0x447a0000
                      );
    }
    fVar10 = (float)FUN_001ada38(param_1);
    fVar10 = *(float *)(iVar6 + 0x38) - fVar10;
    lVar8 = FUN_001ade60(param_1,param_2);
    *(int *)(iVar6 + 0x60) = (int)lVar8;
    if (0.0 < *(float *)(iVar6 + 0x20)) {
      fVar10 = (fVar12 - ABS(fVar10 * 0.5)) / fVar12;
      if (0.0 < fVar10) {
        fVar10 = SQRT(fVar10);
      }
      else {
        fVar10 = 0.0;
      }
      fVar10 = (float)FUN_00204ea0(fVar10);
      fVar11 = *(float *)(iVar6 + 0x40);
      fVar10 = fVar10 * fVar12 * 0.9999999;
      fVar13 = (fVar10 + fVar10) / fVar13 + 0.5;
      *(float *)(iVar6 + 0x48) = fVar11 - fVar13;
      if (fVar11 - fVar13 < 10.0) {
        fVar10 = fVar9;
        if ((fVar13 < fVar11) && (fVar13 != 0.0)) {
          fVar10 = fVar11 / fVar13;
        }
        fVar9 = 0.5;
        if (0.5 <= fVar10) {
          fVar9 = (float)((int)fVar10 * (uint)(fVar10 < 100.0) |
                         (uint)(fVar10 >= 100.0) * 0x42c80000);
        }
        *(float *)(iVar6 + 0x44) = fVar12 * fVar9;
      }
      lVar8 = 1;
    }
    iVar1 = (**(code **)(&DAT_0023cf9c + *piVar7 * 0x5c))(param_1,3);
    iVar2 = *(int *)(iVar6 + 100);
    iVar1 = *(int *)(iVar1 + 4);
    iVar4 = *(int *)(iVar1 + 0x34);
    iVar5 = *(int *)(iVar1 + 0x38);
    if (*(int *)(iVar6 + 0x60) == 0) {
      if (iVar2 != 0) {
        if (iVar5 < 0) {
          if (*(float *)(iVar6 + 0x48) <= 0.5) {
            iVar2 = 0;
            iVar4 = iVar5;
          }
        }
        else {
          if (iVar4 == iVar5) {
            *(int *)(iVar6 + 100) = iVar2;
            goto LAB_001aadd8;
          }
          if (*(float *)(iVar6 + 0x48) <= 0.5) {
            iVar2 = 0;
            iVar4 = iVar5;
          }
        }
        *(int *)(iVar6 + 100) = iVar2;
        iVar5 = iVar4;
        goto LAB_001aadd8;
      }
      *(int *)(iVar1 + 0x38) = iVar5;
    }
    else {
      *(undefined4 *)(iVar6 + 100) = 1;
LAB_001aadd8:
      *(int *)(iVar1 + 0x38) = iVar5;
    }
    iVar2 = *(int *)(iVar6 + 0x60);
  }
  if ((iVar2 == 0) &&
     (fVar13 = *(float *)(*(short *)(piVar7[1] + 0x16) * 4 + *(int *)(iRam00290534 + 0x3c)),
     fVar13 < 500.0)) {
    iVar2 = 1;
    if (*(float *)(iVar6 + 0x24) + (*(float *)(iVar6 + 0x28) - *(float *)(iVar6 + 0x24)) * 0.5 < 0.0
       ) {
      iVar2 = -1;
    }
    iVar1 = 1;
    if (fVar13 < 0.0) {
      iVar1 = -1;
    }
    if (iVar2 == iVar1) {
      if (0.5 < fVar9) {
        return 0;
      }
      goto LAB_001aaea8;
    }
  }
  if ((lVar8 != 0) && (*(int *)(iVar6 + 100) != 0)) {
    uVar3 = FUN_001ab338(param_1,param_2,param_3);
    return uVar3;
  }
LAB_001aaea8:
  uVar3 = FUN_001aaef0(param_1,param_2,param_3);
  return uVar3;
}

