
void FUN_001c3ad0(undefined4 param_1,undefined4 param_2,undefined8 param_3,long param_4,long param_5
                 )

{
  char cVar1;
  char *pcVar2;
  uint uVar3;
  bool bVar4;
  int iVar5;
  undefined4 uVar6;
  undefined4 uVar7;
  undefined1 in_zero_qw [16];
  undefined1 uVar8;
  int iVar9;
  undefined8 uVar10;
  undefined8 extraout_v0_udw;
  undefined4 *puVar11;
  undefined1 (*pauVar12) [16];
  undefined1 (*pauVar13) [16];
  int *piVar14;
  undefined1 (*pauVar15) [16];
  undefined1 auVar16 [16];
  int *piVar17;
  int iVar18;
  int iVar19;
  int iVar20;
  int iVar21;
  undefined *puVar22;
  undefined4 *puVar23;
  int iVar24;
  undefined4 uVar25;
  float fVar26;
  float fVar27;
  float fVar28;
  undefined1 in_vf0 [16];
  undefined1 auVar29 [16];
  undefined1 auVar30 [16];
  undefined1 auStack_d0 [16];
  undefined1 auStack_c0 [16];
  undefined1 auStack_b0 [16];
  undefined1 auStack_90 [16];
  undefined4 auStack_80 [4];
  
  fVar28 = 0.0;
  piVar17 = (int *)param_3;
  pcVar2 = (char *)*piVar17;
  cVar1 = *pcVar2;
  if (cVar1 < '\0') {
    puVar22 = (undefined *)0x0;
    iVar9 = *(int *)(pcVar2 + 8);
  }
  else {
    puVar22 = &DAT_00241b40 + (cVar1 * 0x14 + (int)cVar1) * 0x10;
    iVar9 = *(int *)(pcVar2 + 8);
  }
  iVar9 = *(int *)(iVar9 + 4);
  piVar17[0x13] = 0x40a00000;
  iVar9 = *(int *)(iVar9 + 0x14c);
  iVar18 = 0;
  piVar17[1] = 1;
  iVar20 = 3;
  iVar24 = *(int *)(iVar9 + 0x18c);
  iVar19 = *(int *)(iVar9 + 0x17c);
  iVar9 = *(int *)(iVar9 + 0x188);
  piVar17[0x14] = 0;
  piVar17[0x15] = 0;
  piVar17[0x16] = 0;
  piVar17[0x17] = 0;
  piVar17[0x18] = 0;
  piVar17[0x19] = 0;
  piVar17[5] = 0;
  piVar17[6] = 0;
  piVar17[7] = 0;
  piVar17[8] = 0;
  piVar17[10] = 0;
  piVar17[9] = 0;
  piVar17[0xb] = 0;
  piVar17[0xc] = 0;
  piVar17[0xd] = 0;
  piVar17[0xe] = 0;
  piVar17[0xf] = 0;
  piVar17[0x10] = 0;
  *(undefined1 *)((int)piVar17 + 0x12) = 0;
  *(undefined1 *)((int)piVar17 + 0xd) = 0;
  *(undefined1 *)((int)piVar17 + 0xe) = 0;
  *(undefined1 *)((int)piVar17 + 0xf) = 0;
  *(undefined1 *)(piVar17 + 4) = 0;
  *(undefined1 *)((int)piVar17 + 0x11) = 0;
  *(undefined1 *)((int)piVar17 + 0x13) = 0;
  piVar17[0x11] = 0;
  piVar17[0x12] = 0;
  piVar17[0x1a] = 0;
  piVar17[0x1b] = 0;
  piVar17[0x1c] = 0;
  piVar17[0x1d] = 0;
  piVar17[0x1e] = 0;
  piVar17[0x1f] = 0;
  piVar17[0x20] = 0;
  piVar17[0x21] = 0;
  piVar17[0x22] = 0;
  piVar17[0x23] = 0;
  piVar17[0x24] = 0;
  piVar17[0x25] = 0;
  iVar24 = *(int *)(iVar24 + 0x14);
  piVar17[0x27] = 0;
  piVar17[0x26] = iVar24;
  FUN_0020c7fc(piVar17 + 0x28,0,0x10);
  piVar17[0x2c] = 0;
  piVar17[0x2d] = 0;
  FUN_0020c7fc(piVar17 + 0x2e,0,0x10);
  piVar17[0x32] = 0;
  iVar24 = *piVar17;
  *(undefined1 *)(piVar17 + 0x38) = 1;
  piVar17[0x3c] = 0x3f800000;
  *(undefined4 *)(iVar24 + 0x4b0) = 0;
  *(undefined4 *)(iVar24 + 0x4b4) = 0;
  *(undefined4 *)(iVar24 + 0x4b8) = 0;
  *(undefined4 *)(iVar24 + 0x4bc) = 0;
  *(undefined4 *)(iVar24 + 0x6a0) = 0;
  *(undefined4 *)(iVar24 + 0x6a4) = 0;
  *(undefined4 *)(iVar24 + 0x6a8) = 0;
  *(undefined4 *)(iVar24 + 0x6ac) = 0;
  *(undefined4 *)(iVar24 + 0x500) = 0;
  *(undefined4 *)(iVar24 + 0x504) = 0;
  *(undefined4 *)(iVar24 + 0x508) = 0;
  *(undefined4 *)(iVar24 + 0x50c) = 0;
  *(undefined4 *)(iVar24 + 0x5a0) = 0;
  *(undefined4 *)(iVar24 + 0x5a4) = 0;
  *(undefined4 *)(iVar24 + 0x5a8) = 0;
  *(undefined4 *)(iVar24 + 0x5ac) = 0;
  *(undefined4 *)(iVar24 + 0x550) = 0;
  *(undefined4 *)(iVar24 + 0x554) = 0;
  *(undefined4 *)(iVar24 + 0x558) = 0;
  *(undefined4 *)(iVar24 + 0x55c) = 0;
  piVar17[0x33] = 0;
  piVar17[0x34] = 0;
  piVar17[0x35] = 0;
  piVar17[0x36] = 0;
  piVar17[0x37] = 0;
  piVar17[0x39] = 0;
  piVar17[0x3d] = 0x3f800000;
  uVar25 = FUN_00114d58(param_1);
  uVar10 = FUN_001e0818(uVar25,0);
  iVar24 = *piVar17;
  *(int *)(puVar22 + 0x1c) = (int)uVar10;
  iVar24 = *(int *)(*(int *)(iVar24 + 8) + 4);
  *(undefined4 *)(iVar24 + 0x70) = param_1;
  *(undefined4 *)(iVar24 + 0x74) = uVar25;
  *(undefined4 *)(iVar24 + 0x78) = param_1;
  *(undefined4 *)(iVar24 + 0x7c) = uVar25;
  *(short *)(iVar24 + 0x16) = (short)uVar10;
  *(undefined4 *)(puVar22 + 0x34) = param_1;
  *(undefined4 *)(puVar22 + 0x38) = uVar25;
  FUN_001df900(uVar25,param_2,uVar10,auStack_90);
  do {
    auVar16 = _pextuw(in_zero_qw,auStack_90);
    iVar20 = iVar20 + -1;
    iVar24 = *(int *)(*piVar17 + 0x6f0) + iVar18;
    FUN_00133ca0(auStack_90._0_4_,auVar16._0_4_,auStack_80,iVar24 + 0xf0,
                 *(undefined4 *)(iVar24 + 0x114));
    uVar8 = FUN_00134970(*(undefined4 *)(iVar18 + *(int *)(*piVar17 + 0x6f0) + 0x114));
    *(undefined1 *)(iVar18 + *(int *)(*piVar17 + 0x6f0) + 7) = uVar8;
    uVar8 = FUN_001c3590(*(undefined1 *)(iVar18 + *(int *)(*piVar17 + 0x6f0) + 7));
    iVar24 = iVar18 + *(int *)(*piVar17 + 0x6f0);
    iVar18 = iVar18 + 0x130;
    *(undefined1 *)(iVar24 + 6) = uVar8;
  } while (-1 < iVar20);
  iVar24 = 4;
  _lqc2(auStack_90);
  auVar16 = _qmtc2(auStack_80[0]);
  auVar29 = _vaddbc(in_vf0,auVar16);
  auVar30 = _vmove(auVar29);
  auVar16 = _qmtc2(0x3f000000);
  auVar16 = _vaddbc(auVar30,auVar16);
  _sqc2(auVar29);
  auStack_90 = _sqc2(auVar16);
  puVar11 = (undefined4 *)(*piVar17 + 0x640);
  auVar16 = _qmfc2(auVar16._0_4_);
  do {
    iVar24 = iVar24 + -1;
    *puVar11 = auVar16._0_4_;
    puVar11[1] = auVar16._4_4_;
    puVar11[2] = auVar16._8_4_;
    puVar11[3] = auVar16._12_4_;
    puVar11 = puVar11 + -4;
  } while (-1 < iVar24);
  FUN_00114080(auStack_d0);
  auVar16 = _pextlw(0,0);
  auVar29 = _pextlw(0,0x3f800000);
  auStack_b0 = _pcpyld(auVar29,auVar16);
  if (param_4 != 0) {
    fVar28 = (float)FUN_001151d8(*(undefined8 *)param_4);
    if (fVar28 <= 0.0) {
      iVar24 = *piVar17;
      goto LAB_001c3e40;
    }
    auStack_b0._0_8_ = FUN_001150f0(fVar28,*(undefined8 *)param_4);
    auStack_b0._8_4_ = (int)extraout_v0_udw;
    auStack_b0._12_4_ = (int)((ulong)extraout_v0_udw >> 0x20);
  }
  iVar24 = *piVar17;
LAB_001c3e40:
  iVar18 = 0;
  auVar16 = _lqc2(auStack_b0);
  auVar30 = _lqc2(*(undefined1 (*) [16])(*(int *)(iVar24 + 0x6f0) + 0xf0));
  _vopmula(auVar30,auVar16);
  auVar16 = _vopmsub(auVar16,auVar30);
  auVar16 = _vsub(auVar16,auVar16);
  _vopmula(auVar16,auVar30);
  auVar29 = _vopmsub(auVar30,auVar16);
  auVar29 = _vsub(auVar29,auVar29);
  auStack_d0 = _sqc2(auVar16);
  auStack_c0 = _sqc2(auVar30);
  auStack_b0 = _sqc2(auVar29);
  while( true ) {
    iVar20 = iVar18 * 0x40;
    iVar18 = iVar18 + 1;
    pauVar12 = (undefined1 (*) [16])(iVar24 + iVar20 + 0x30);
    *(undefined4 *)*pauVar12 = auStack_d0._0_4_;
    *(undefined4 *)(*pauVar12 + 4) = auStack_d0._4_4_;
    *(undefined4 *)(*pauVar12 + 8) = auStack_d0._8_4_;
    *(undefined4 *)(*pauVar12 + 0xc) = auStack_d0._12_4_;
    pauVar13 = (undefined1 (*) [16])(iVar24 + iVar20 + 0x40);
    pauVar15 = (undefined1 (*) [16])(iVar24 + iVar20 + 0x50);
    *(int *)*pauVar13 = auStack_c0._0_4_;
    *(int *)(*pauVar13 + 4) = auStack_c0._4_4_;
    *(int *)(*pauVar13 + 8) = auStack_c0._8_4_;
    *(int *)(*pauVar13 + 0xc) = auStack_c0._12_4_;
    *(undefined4 *)*pauVar15 = auStack_b0._0_4_;
    *(undefined4 *)(*pauVar15 + 4) = auStack_b0._4_4_;
    *(undefined4 *)(*pauVar15 + 8) = auStack_b0._8_4_;
    *(undefined4 *)(*pauVar15 + 0xc) = auStack_b0._12_4_;
    auVar16 = _lqc2(*pauVar12);
    auVar16 = _vsub(auVar16,auVar16);
    auVar16 = _sqc2(auVar16);
    *pauVar12 = auVar16;
    auVar16 = _lqc2(*pauVar13);
    auVar16 = _vsub(auVar16,auVar16);
    auVar16 = _sqc2(auVar16);
    *pauVar13 = auVar16;
    auVar16 = _lqc2(*pauVar15);
    auVar16 = _vsub(auVar16,auVar16);
    auVar16 = _sqc2(auVar16);
    *pauVar15 = auVar16;
    FUN_00114080(iVar24 + iVar20 + 0x170);
    if (4 < iVar18) break;
    iVar24 = *piVar17;
  }
  iVar24 = 4;
  if (param_5 != 0) {
    iVar18 = *piVar17;
    puVar11 = (undefined4 *)(iVar18 + 0x650);
    do {
      puVar23 = (undefined4 *)param_5;
      uVar25 = puVar23[1];
      uVar6 = puVar23[2];
      uVar7 = puVar23[3];
      iVar24 = iVar24 + -1;
      *puVar11 = *puVar23;
      puVar11[1] = uVar25;
      puVar11[2] = uVar6;
      puVar11[3] = uVar7;
      puVar11 = puVar11 + 4;
    } while (-1 < iVar24);
    iVar21 = 0;
    iVar24 = *(int *)(iVar18 + 0x6f0);
    iVar20 = *(int *)(*(int *)(*(int *)(iVar18 + 8) + 4) + 0x14c);
    piVar17[0x32] = (int)fVar28;
    piVar14 = (int *)(iVar24 + 0x120);
    do {
      bVar4 = 1 < iVar21;
      iVar21 = iVar21 + 1;
      iVar24 = *piVar14;
      iVar5 = 1;
      if (bVar4) {
        iVar5 = 2;
      }
      piVar14 = piVar14 + 0x4c;
      *(float *)(iVar24 + 0xec) =
           fVar28 * 60.0 * *(float *)(*(int *)(iVar5 * 4 + iVar20 + 0x194) + 0x3c) * 0.15915494;
    } while (iVar21 < 4);
    iVar24 = FUN_0019c1d8(*(undefined4 *)(iVar18 + 8));
    iVar18 = *(char *)(iVar19 + 0x14) + -2;
    fVar27 = 0.0;
    fVar28 = fVar28 * 60.0 * *(float *)(iVar24 + 0x3c) * 0.15915494;
    if (1 < iVar18) {
      fVar26 = *(float *)(iVar9 + 0x28);
      fVar27 = *(float *)(iVar18 * 4 + iVar19 + 0xc + 0x14);
      while ((fVar27 = *(float *)(iVar19 + 0x20) * fVar27 * fVar28, fVar27 <= fVar26 * 0.25 ||
             (fVar26 * 0.75 <= fVar27))) {
        iVar18 = iVar18 + -1;
        if (iVar18 < 2) break;
        fVar27 = *(float *)(iVar18 * 4 + iVar19 + 0xc + 0x14);
      }
    }
    *(char *)((int)piVar17 + 0x11) = (char)iVar18;
    piVar17[0x21] = (int)fVar27;
    piVar17[0x24] = (int)fVar28;
    piVar17[0x1c] = (int)fVar27;
  }
  iVar9 = *piVar17;
  iVar18 = 0;
  iVar24 = 0;
  iVar19 = 0;
  do {
    if (*(int *)(iVar24 + *(int *)(iVar9 + 0x6f0) + 0x120) != 0) {
      pauVar12 = (undefined1 (*) [16])(iVar19 * 0x10 + *(int *)(iVar9 + 0x6f0));
      auVar16 = _qmtc2(0);
      iVar20 = 4;
      do {
        pauVar12 = pauVar12 + 1;
        _lqc2(*pauVar12);
        auVar29 = _vaddbc(in_vf0,auVar16);
        iVar20 = iVar20 + -1;
        auVar29 = _sqc2(auVar29);
        *pauVar12 = auVar29;
      } while (-1 < iVar20);
    }
    iVar18 = iVar18 + 1;
    iVar19 = iVar19 + 0x13;
    *(undefined1 *)(iVar24 + *(int *)(iVar9 + 0x6f0) + 5) = 1;
    iVar9 = *piVar17;
    iVar20 = *(int *)(iVar9 + 0x6f0);
    iVar21 = iVar24 + iVar20;
    uVar25 = *(undefined4 *)(iVar20 + 0x114);
    auVar29 = _lqc2(*(undefined1 (*) [16])(iVar21 + 0x60));
    *(undefined4 *)(iVar21 + 0x108) = 0;
    auVar16 = _sqc2(auVar29);
    *(undefined1 (*) [16])(iVar21 + 0xe0) = auVar16;
    *(undefined4 *)(iVar21 + 0x110) = *(undefined4 *)(iVar21 + 0x10c);
    auVar16 = _lqc2(*(undefined1 (*) [16])(iVar9 + 0x600));
    auVar16 = _vadd(auVar29,auVar16);
    auVar16 = _qmfc2(auVar16._0_4_);
    auVar29 = _pextuw(in_zero_qw,auVar16);
    *(int *)(iVar21 + 0xe0) = auVar16._0_4_;
    *(int *)(iVar21 + 0xe4) = auVar16._4_4_;
    *(int *)(iVar21 + 0xe8) = auVar16._8_4_;
    *(int *)(iVar21 + 0xec) = auVar16._12_4_;
    FUN_00133ca0(auVar16._0_4_,auVar29._0_4_,auStack_80,iVar20 + 0xf0,uVar25);
    iVar9 = *piVar17;
    auVar16 = _qmtc2(auStack_80[0]);
    iVar20 = iVar24 + *(int *)(iVar9 + 0x6f0);
    iVar24 = iVar24 + 0x130;
    _lqc2(*(undefined1 (*) [16])(iVar20 + 0xe0));
    auVar29 = _vaddbc(in_vf0,auVar16);
    auVar16 = _sqc2(auVar29);
    *(undefined1 (*) [16])(iVar20 + 0xb0) = auVar16;
    auVar16 = _sqc2(auVar29);
    *(undefined1 (*) [16])(iVar20 + 0xe0) = auVar16;
    auVar16 = _sqc2(auVar29);
    *(undefined1 (*) [16])(iVar20 + 0xc0) = auVar16;
    auVar16 = *(undefined1 (*) [16])(iVar9 + 0x50);
    *(int *)(iVar20 + 0xa0) = auVar16._0_4_;
    *(int *)(iVar20 + 0xa4) = auVar16._4_4_;
    *(int *)(iVar20 + 0xa8) = auVar16._8_4_;
    *(int *)(iVar20 + 0xac) = auVar16._12_4_;
  } while (iVar18 < 0xc);
  FUN_001c9a90(param_3);
  iVar9 = *(int *)(*(int *)(*piVar17 + 8) + 4);
  iVar24 = *(int *)(iVar9 + 0xe4);
  *(undefined8 *)(iVar24 + 0x10) = *(undefined8 *)(iVar9 + 0x20);
  *(undefined8 *)(iVar24 + 0x18) = *(undefined8 *)(iVar9 + 0x28);
  *(undefined8 *)(iVar24 + 0x20) = *(undefined8 *)(iVar9 + 0x30);
  *(undefined8 *)(iVar24 + 0x28) = *(undefined8 *)(iVar9 + 0x38);
  *(undefined8 *)(iVar24 + 0x30) = *(undefined8 *)(iVar9 + 0x40);
  *(undefined8 *)(iVar24 + 0x38) = *(undefined8 *)(iVar9 + 0x48);
  *(undefined8 *)(iVar24 + 0x40) = *(undefined8 *)(iVar9 + 0x50);
  *(undefined8 *)(iVar24 + 0x48) = *(undefined8 *)(iVar9 + 0x58);
  FUN_001c9790(param_3);
  iVar9 = (**(code **)(&DAT_0023cf9c + **(int **)(*piVar17 + 8) * 0x5c))(*(int **)(*piVar17 + 8),3);
  uVar3 = *(uint *)(*(int *)(iVar9 + 4) + 0x28);
  if (uVar3 < 2) {
    FUN_00109040(uVar3,1);
  }
  return;
}

