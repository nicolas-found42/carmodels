
/* source file (string position, lower evidence than a direct reference):
   ../fr2/source/hscore/hscore.c */

undefined8 FUN_001ad3f8(undefined8 param_1,undefined8 param_2)

{
  undefined1 (*pauVar1) [16];
  short sVar2;
  undefined2 uVar3;
  int iVar4;
  undefined1 auVar5 [12];
  undefined1 in_zero_qw [16];
  int iVar6;
  undefined8 uVar7;
  int iVar8;
  undefined1 auVar9 [16];
  float *pfVar10;
  int iVar11;
  int *piVar12;
  int iVar13;
  int iVar14;
  int iVar15;
  undefined4 uVar16;
  undefined4 uVar17;
  float fVar18;
  float fVar19;
  float fVar20;
  float fVar21;
  float fVar22;
  float fVar23;
  float fVar24;
  float fVar25;
  float fVar26;
  float fVar27;
  undefined1 auVar28 [16];
  undefined1 auVar29 [16];
  float afStack_220 [16];
  undefined1 auStack_1e0 [216];
  undefined1 auStack_108 [40];
  int iStack_e0;
  undefined1 auStack_dc [12];
  undefined1 auStack_d0 [16];
  int iStack_c0;
  undefined4 uStack_bc;
  
  pfVar10 = afStack_220;
  iVar13 = 0;
  iVar14 = -1;
  iVar15 = 0;
  uVar16 = 0;
  FUN_001ae3b8();
  piVar12 = (int *)param_1;
  iVar6 = (**(code **)(&DAT_0023cf9c + *piVar12 * 0x5c))(param_1,3);
  FUN_0020c7fc(afStack_220,0,0x38);
  iVar8 = piVar12[1];
  iStack_e0 = 0xe;
  sVar2 = *(short *)(iVar8 + 0x16);
  iVar4 = *(int *)(iVar6 + 4);
  iVar11 = (int)param_2;
  *(undefined4 *)(iVar11 + 0x18) = 0;
  iStack_c0 = (int)sVar2;
  uStack_bc = *(undefined4 *)(iVar4 + 0x34);
  fVar27 = *(float *)(iVar8 + 0x74);
  FUN_001ac7f8(auStack_1e0,param_1);
  FUN_001aca10(auStack_1e0,param_1);
  FUN_001acdf8(auStack_1e0,param_1,param_2);
  FUN_001ad078(auStack_1e0,param_1,param_2);
  FUN_0020cb30(auStack_108,6,4,0x1adf08);
  FUN_001ad228(auStack_1e0,afStack_220,auStack_dc,&iStack_e0);
  fVar18 = DAT_00290014;
  iVar8 = piVar12[1];
  fVar26 = *(float *)(iVar8 + 0x118) + *(float *)(iVar8 + 0x114);
  pauVar1 = (undefined1 (*) [16])(*(int *)(*(int *)(iVar8 + 0x14c) + 0x174) + 0x50);
  auVar5 = *(undefined1 (*) [12])*pauVar1;
  auVar9 = _pextuw(in_zero_qw,*pauVar1);
  fVar24 = auVar9._0_4_;
  FUN_001e0a88(*(undefined4 *)(iVar8 + 0x74),*(undefined2 *)(iVar8 + 0x16),auStack_d0);
  auVar9 = _lqc2(auStack_d0);
  auVar28 = _lqc2(*(undefined1 (*) [16])(iVar8 + 0x20));
  auVar28 = _vmul(auVar9,auVar28);
  auVar29 = _lqc2(*(undefined1 (*) [16])(iVar8 + 0x40));
  auVar9 = _vmul(auVar9,auVar29);
  auVar28 = _vaddbc(auVar28,auVar28);
  auVar29 = _vaddbc(auVar28,auVar28);
  auVar9 = _vaddbc(auVar9,auVar9);
  auVar28 = _vaddbc(auVar9,auVar9);
  auVar9 = _qmfc2(auVar29._0_4_);
  auVar28 = _qmfc2(auVar28._0_4_);
  fVar24 = ABS(auVar9._0_4_) * auVar5._0_4_ + ABS(auVar28._0_4_) * fVar24;
  if (0 < iStack_e0) {
    fVar25 = 0.0;
    iVar8 = iStack_e0;
    do {
      fVar21 = pfVar10[1] - *pfVar10;
      fVar23 = *pfVar10 + fVar21 * 0.5;
      fVar22 = ABS(fVar23 - fVar26);
      fVar21 = ABS(fVar21);
      if (fVar24 < fVar22) {
        fVar22 = fVar22 - (fVar21 - fVar24);
      }
      if ((fVar24 <= fVar21) && (fVar22 < fVar18)) {
        if (*(int *)(iVar11 + 0x18) == 0) {
          fVar20 = (float)FUN_001ae338(param_1);
          uVar17 = FUN_00114d58(fVar27 + fVar20 * *(float *)(iRam00290534 + 0x58));
          uVar7 = FUN_001e0818(uVar17,iStack_c0);
        }
        else {
          iVar8 = *(int *)(*(int *)(iVar11 + 0x18) + 4);
          uVar3 = *(undefined2 *)(iVar8 + 0x16);
          fVar20 = *(float *)(iVar11 + 0x40) * ABS(*(float *)(piVar12[1] + 0xec));
          fVar20 = (float)((int)fVar20 * (uint)(fVar25 < fVar20) |
                          (int)fVar25 * (uint)(fVar25 >= fVar20));
          uVar17 = FUN_00114d58(*(float *)(iVar8 + 0x74) + fVar20 / *(float *)(iRam00290534 + 0x54))
          ;
          uVar7 = FUN_001e0818(uVar17,uVar3);
        }
        FUN_001e0d90(uVar17,uVar7);
        iVar8 = iStack_e0;
        if (fVar20 < 1000.0) {
          fVar18 = *pfVar10;
          fVar19 = pfVar10[1];
          fVar20 = fVar18;
          if (ABS(fVar18) <= ABS(fVar19)) {
            fVar20 = fVar19;
            fVar19 = fVar18;
          }
          iVar4 = *(int *)(iVar6 + 4);
          *(float *)(iVar11 + 0x38) = fVar23;
          *(int *)(iVar4 + 0x34) = iVar13;
          fVar18 = fVar22;
          iVar14 = iVar13;
          if (fVar24 < fVar21) {
            fVar21 = fVar24;
            if (fVar20 - fVar19 < fVar25) {
              fVar21 = -fVar24;
            }
            *(float *)(iVar11 + 0x38) = fVar19 + fVar21 * 0.5;
          }
        }
        else {
          uVar16 = 1;
        }
      }
      iVar15 = iVar15 + 1;
      pfVar10 = pfVar10 + 2;
      iVar13 = iVar13 + 2;
    } while (iVar15 < iVar8);
  }
  if (-1 < iVar14) {
    *(float *)(iVar11 + 0x3c) = fVar18;
    uVar16 = 1;
    fVar18 = afStack_220[iVar14 + 1];
    *(float *)(iVar11 + 0x24) = afStack_220[iVar14];
    *(float *)(iVar11 + 0x28) = fVar18;
  }
  if (iVar14 == -1) {
    iVar8 = *(int *)(iVar6 + 4);
    *(float *)(iVar11 + 0x24) = afStack_220[0];
    *(undefined4 *)(iVar8 + 0x34) = 0xffffffff;
    *(float *)(iVar11 + 0x28) = afStack_220[1];
    *(undefined4 *)(iVar11 + 0x3c) = 0;
    *(undefined4 *)(iVar11 + 100) = uVar16;
  }
  else {
    *(undefined4 *)(iVar11 + 100) = uVar16;
  }
  return 1;
}

