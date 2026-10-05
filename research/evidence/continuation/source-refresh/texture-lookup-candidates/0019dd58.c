
/* source file (direct reference to its __FILE__ string, not proof of authorship):
   ../fr2/source/entity/mobile/vehicle/car/cr_updt.c:303 */

void FUN_0019dd58(int param_1,long param_2)

{
  int iVar1;
  int iVar2;
  undefined1 (*pauVar3) [16];
  float fVar4;
  float fVar5;
  float fVar6;
  float fVar7;
  float fVar8;
  undefined1 auVar9 [16];
  undefined1 auVar10 [16];
  
  fVar4 = 0.0;
  iVar1 = *(int *)(param_1 + 4);
  fVar6 = *(float *)(iVar1 + 0xfc);
  iVar2 = *(int *)(iVar1 + 0xe0);
  pauVar3 = (undefined1 (*) [16])param_2;
  if (0.0 < fVar6) {
    fVar7 = *(float *)(pauVar3[1] + 8) / fVar6;
    if (0.0 <= fVar7) {
      fVar4 = (float)((int)fVar7 * (uint)(fVar7 < 1.0) | (uint)(fVar7 >= 1.0) * 0x3f800000);
      fVar7 = *(float *)pauVar3[1];
    }
    else {
      fVar7 = *(float *)pauVar3[1];
    }
    fVar8 = -1.0;
    fVar7 = fVar7 / fVar6;
    if (-1.0 <= fVar7) {
      fVar8 = (float)((int)fVar7 * (uint)(fVar7 < 0.0));
    }
    fVar8 = ABS(fVar8);
  }
  else {
    fVar4 = 0.0;
    fVar8 = 0.0;
  }
  fVar6 = (float)FUN_001c9f28(*(undefined4 *)(iVar1 + 0xec),
                              *(undefined4 *)(*(int *)(iVar1 + 0x14c) + 0x184));
  if (param_2 == 0) {
                    /* WARNING: Subroutine does not return */
    FUN_00105888(0x261c80,0x12f,0x261cd8);
  }
  iVar1 = *(int *)(param_1 + 4);
  fVar5 = -fVar6;
  auVar10 = _lqc2(*pauVar3);
  auVar9 = _lqc2(*(undefined1 (*) [16])(iVar1 + 0x20));
  auVar9 = _vmul(auVar9,auVar10);
  auVar9 = _vaddbc(auVar9,auVar9);
  auVar9 = _vaddbc(auVar9,auVar9);
  auVar9 = _qmfc2(auVar9._0_4_);
  fVar7 = auVar9._0_4_;
  if (fVar5 <= fVar7) {
    fVar5 = (float)((int)fVar7 * (uint)(fVar7 < fVar6) | (int)fVar6 * (uint)(fVar7 >= fVar6));
  }
  *(float *)(iVar1 + 0x10c) = fVar5 / fVar6;
  *(float *)(iVar1 + 0x110) = fVar4;
  *(float *)(iVar1 + 0xf8) = fVar8;
  if (0.0 < fVar4) {
    *(float *)(iVar2 + 0x28) = fVar4;
    *(undefined4 *)(iVar2 + 0x2c) = 0;
  }
  else {
    *(float *)(iVar2 + 0x2c) = fVar8;
    *(undefined4 *)(iVar2 + 0x28) = 0;
  }
  *(float *)(iVar2 + 0x40) = fVar5 / fVar6;
  return;
}

