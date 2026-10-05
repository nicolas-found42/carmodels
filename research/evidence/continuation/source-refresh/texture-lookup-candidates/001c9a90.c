
void FUN_001c9a90(int *param_1)

{
  char cVar1;
  char *pcVar2;
  int iVar3;
  undefined1 auVar4 [12];
  undefined4 uVar5;
  undefined4 uVar6;
  int iVar7;
  long lVar8;
  undefined4 uVar9;
  undefined4 *puVar10;
  int iVar11;
  undefined *puVar12;
  int iVar13;
  float fVar14;
  undefined1 auVar15 [16];
  undefined1 auVar16 [16];
  undefined1 auVar17 [16];
  
  pcVar2 = (char *)*param_1;
  cVar1 = *pcVar2;
  if (cVar1 < '\0') {
    puVar12 = (undefined *)0x0;
    iVar7 = *(int *)(pcVar2 + 8);
  }
  else {
    puVar12 = &DAT_00241b40 + (cVar1 * 0x14 + (int)cVar1) * 0x10;
    iVar7 = *(int *)(pcVar2 + 8);
  }
  FUN_00114098(*(int *)(iVar7 + 4) + 0x20,pcVar2 + 0x30);
  iVar7 = *param_1;
  iVar13 = param_1[0x1c];
  uVar9 = *(undefined4 *)(iVar7 + 0x604);
  uVar5 = *(undefined4 *)(iVar7 + 0x608);
  uVar6 = *(undefined4 *)(iVar7 + 0x60c);
  iVar11 = *(int *)(*(int *)(iVar7 + 8) + 4);
  *(undefined4 *)(iVar11 + 0x50) = *(undefined4 *)(iVar7 + 0x600);
  *(undefined4 *)(iVar11 + 0x54) = uVar9;
  *(undefined4 *)(iVar11 + 0x58) = uVar5;
  *(undefined4 *)(iVar11 + 0x5c) = uVar6;
  *(int *)(iVar11 + 0xf4) = iVar13;
  auVar4 = *(undefined1 (*) [12])(iVar7 + 0x650);
  uVar9 = *(undefined4 *)(iVar7 + 0x65c);
  iVar13 = param_1[0x2c];
  *(int *)(iVar11 + 0x60) = auVar4._0_4_;
  *(int *)(iVar11 + 100) = auVar4._4_4_;
  *(int *)(iVar11 + 0x68) = auVar4._8_4_;
  *(undefined4 *)(iVar11 + 0x6c) = uVar9;
  *(int *)(iVar11 + 0x100) = iVar13;
  auVar16 = _lqc2(*(undefined1 (*) [16])(iVar7 + 0x40));
  auVar17 = _lqc2(*(undefined1 (*) [16])(iVar7 + 0x650));
  auVar15 = _vmul(auVar17,auVar16);
  auVar15 = _vaddbc(auVar15,auVar15);
  auVar15 = _vaddbc(auVar15,auVar15);
  auVar15 = _qmfc2(auVar15._0_4_);
  auVar15 = _qmtc2(-auVar15._0_4_);
  auVar15 = _vmulbc(auVar16,auVar15);
  auVar15 = _vadd(auVar15,auVar17);
  auVar15 = _qmfc2(auVar15._0_4_);
  fVar14 = (float)FUN_001151d8(auVar15._0_8_);
  iVar7 = *param_1;
  puVar10 = (undefined4 *)(puVar12 + 0x80);
  iVar11 = *(int *)(iVar7 + 0x6f0);
  iVar13 = 3;
  *(float *)(*(int *)(*(int *)(iVar7 + 8) + 4) + 0xec) = fVar14;
  *(undefined4 *)(puVar12 + 0x4c) = 0x42c80000;
  do {
    iVar3 = *(int *)(iVar11 + 0x120);
    iVar13 = iVar13 + -1;
    auVar15 = _prot3w(*(undefined1 (*) [16])(iVar11 + 0x10));
    iVar11 = iVar11 + 0x130;
    puVar10[-4] = *(undefined4 *)(iVar3 + 0xe0);
    uVar9 = *(undefined4 *)(iVar3 + 0xf8);
    puVar10[-0xc] = auVar15._0_4_;
    puVar10[-8] = uVar9;
    *puVar10 = *(undefined4 *)(iVar3 + 0xec);
    puVar10 = puVar10 + 1;
  } while (-1 < iVar13);
  *(float *)(puVar12 + 0x44) = fVar14;
  iVar7 = *(int *)(iVar7 + 8);
  iVar11 = *(int *)(iVar7 + 4);
  *(int *)(puVar12 + 0x3c) = param_1[0x1c];
  iVar11 = *(int *)(iVar11 + 300);
  *(int *)(puVar12 + 0x20) = (int)*(char *)((int)param_1 + 0x11);
  if ((iVar11 == 4) && (lVar8 = FUN_001b3e58(iVar7), lVar8 == 0)) {
    FUN_001694b0(fVar14,**(undefined1 **)(*(int *)(iVar7 + 4) + 0x14c));
    FUN_00168dd8(fVar14 * FLOAT_002901c4);
    FUN_00168e08(FLOAT_002901c4,param_1[0xc],param_1[0xd]);
    return;
  }
  return;
}

