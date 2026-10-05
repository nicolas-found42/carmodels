
void FUN_001aa2a0(undefined8 param_1,undefined8 param_2,undefined8 param_3)

{
  short sVar1;
  int iVar2;
  int iVar3;
  uint uVar4;
  int iVar5;
  int iVar6;
  int *piVar7;
  int iVar8;
  int iVar9;
  undefined4 uVar10;
  float fVar11;
  float afStack_50 [4];
  
  piVar7 = (int *)param_1;
  iVar5 = (**(code **)(&DAT_0023cf9c + *piVar7 * 0x5c))(param_1,3);
  sVar1 = *(short *)(piVar7[1] + 0x16);
  iVar2 = *(int *)(piVar7[1] + 0xe0);
  uVar10 = FUN_001ad9f8(param_1);
  iVar8 = (int)param_2;
  *(undefined4 *)(iVar8 + 0x1c) = uVar10;
  uVar10 = FUN_001ada38(param_1);
  iVar3 = iRam00290534;
  *(undefined4 *)(iVar8 + 0x34) = uVar10;
  iVar6 = piVar7[1];
  fVar11 = *(float *)(sVar1 * 4 + *(int *)(iVar3 + 0x34));
  iVar3 = *(int *)(iVar6 + 0x84);
  iVar9 = (int)param_3;
  *(undefined4 *)(iVar9 + 0x28) = 4;
  uVar4 = *(uint *)(iVar3 + 0x18);
  *(float *)(iVar8 + 0x2c) = fVar11 * 0.5;
  if (((uVar4 & 2) == 0) || ((uVar4 & 0x44) == 0)) {
    if (*(int *)(iVar6 + 0x148) == 0xb) {
      if (((uVar4 & 0x44) != 0) || (*(float *)(*(int *)(iVar5 + 4) + 0x20) <= 0.0)) {
        *(undefined4 *)(iVar6 + 0x148) = 0;
      }
      else {
        FUN_001ac080(param_1,param_2,param_3);
      }
      iVar6 = *(int *)(iVar9 + 0x28);
    }
    else if (*(float *)(iVar6 + 0xec) < 20.0) {
      if ((uVar4 & 2) == 0) {
        iVar6 = *(int *)(iVar9 + 0x28);
      }
      else if (0.70699996 < ABS(*(float *)(iVar3 + 0x1c))) {
        *(undefined4 *)(*(int *)(iVar5 + 4) + 0x20) = 0x3fc00000;
        FUN_001ac080(param_1,param_2,param_3);
        iVar6 = *(int *)(iVar9 + 0x28);
      }
      else {
        iVar6 = *(int *)(iVar9 + 0x28);
      }
    }
    else {
      iVar6 = *(int *)(iVar9 + 0x28);
    }
  }
  else {
    iVar6 = *(int *)(iVar9 + 0x28);
  }
  if (iVar6 != 1) {
    FUN_001adb78(param_1,afStack_50,0);
    afStack_50[0] = afStack_50[0] * 0.5;
    if (*(float *)(iVar8 + 0x2c) + afStack_50[0] < ABS(*(float *)(iVar8 + 0x34))) {
      FUN_001abd08(param_1,param_2,param_3);
    }
    if (*(int *)(iVar9 + 0x28) != 1) {
      if ((*(int *)(piVar7[1] + 0x148) == 0xe) || (*(float *)(iVar8 + 0x1c) < -0.099999994)) {
        FUN_001abb78(param_1,param_2,param_3);
        return;
      }
      fVar11 = *(float *)(iVar2 + 0x38);
      goto LAB_001aa4bc;
    }
  }
  fVar11 = *(float *)(iVar2 + 0x38);
LAB_001aa4bc:
  if (0.0 < fVar11) {
    FUN_001cb978(iVar2,0);
    *(undefined4 *)(*(int *)(iVar5 + 4) + 0x30) = 2;
  }
  return;
}

