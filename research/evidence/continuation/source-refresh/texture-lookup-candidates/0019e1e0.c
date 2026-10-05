
void FUN_0019e1e0(undefined8 param_1)

{
  int iVar1;
  int iVar2;
  int iVar3;
  long lVar4;
  int iVar5;
  uint uVar6;
  float fVar7;
  float fVar8;
  undefined4 uVar9;
  float fVar10;
  
  iVar5 = (int)param_1;
  uVar9 = *(undefined4 *)(*(int *)(iVar5 + 4) + 0xe0);
  iVar2 = FUN_001ae3b8();
  iVar1 = *(int *)(*(int *)(iVar2 + 4) + 0x6c);
  iVar3 = FUN_00161410();
  uVar6 = iVar3 + 0x1fU & 0xfffffff0;
  lVar4 = FUN_00161228();
  if ((lVar4 == 1) && (lVar4 = FUN_0015f848(), lVar4 == 0)) {
    iVar3 = *(int *)(iVar5 + 4);
    if ((*(int *)(*(int *)(iVar3 + 0x14c) + 0x140) != 5) || (fVar10 = -0.13, iVar1 != 3)) {
      fVar10 = *(float *)(iVar1 * 4 + uVar6 + 0x58);
    }
  }
  else {
    iVar3 = *(int *)(iVar5 + 4);
    fVar10 = *(float *)(iVar1 * 4 + uVar6 + 0x48);
  }
  if (0.0 < *(float *)(iVar3 + 0x104)) {
    iVar2 = *(int *)(iVar2 + 4) + iVar1 * 0x34 + 0x60;
    fVar8 = *(float *)(iVar2 + 0x18);
    fVar7 = *(float *)(iVar2 + 0x10);
  }
  else {
    iVar2 = *(int *)(iVar2 + 4) + iVar1 * 0x34 + 0x60;
    fVar8 = *(float *)(iVar2 + 0x1c);
    fVar7 = *(float *)(iVar2 + 0x14);
  }
  fVar10 = fVar7 + fVar10 + *(float *)(iVar3 + 0x104) * fVar8;
  if (*(float *)(iVar3 + 0xec) < 25.0) {
    fVar10 = fVar10 + ((float)((int)fVar10 * (uint)(1.0 < fVar10) |
                              (uint)(1.0 >= fVar10) * 0x3f800000) - fVar10) *
                      (1.0 - *(float *)(iVar3 + 0xec) * 0.04);
  }
  FUN_001ca3b8(fVar10,uVar9,2);
  if ((iVar1 == 3) && (*(int *)(*(int *)(*(int *)(iVar5 + 4) + 0x14c) + 0x140) != 3)) {
    FUN_001ca3b8(1.1999999,uVar9,1);
  }
  uVar9 = FUN_0019e980(param_1);
  *(undefined4 *)(*(int *)(iVar5 + 4) + 0x11c) = uVar9;
  uVar9 = FUN_0019eaf8(param_1);
  *(undefined4 *)(*(int *)(iVar5 + 4) + 0xfc) = uVar9;
  return;
}

