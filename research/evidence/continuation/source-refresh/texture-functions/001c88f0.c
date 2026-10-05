
void FUN_001c88f0(int *param_1)

{
  undefined1 in_zero_qw [16];
  int iVar1;
  int iVar2;
  char *pcVar3;
  long lVar4;
  undefined8 uVar5;
  ulong uVar6;
  undefined8 extraout_v0_udw;
  undefined8 extraout_v0_udw_00;
  int iVar7;
  char cVar8;
  char cVar9;
  undefined *puVar10;
  float fVar11;
  float fVar12;
  float fVar13;
  float fVar14;
  float fVar15;
  float fVar16;
  uint uVar17;
  uint uVar18;
  float fVar19;
  undefined1 auVar20 [16];
  undefined4 uStack_60;
  undefined4 uStack_5c;
  undefined4 uStack_58;
  undefined4 uStack_54;
  
  pcVar3 = (char *)*param_1;
  cVar8 = *pcVar3;
  if (cVar8 < '\0') {
    puVar10 = (undefined *)0x0;
    fVar15 = (float)param_1[0x32];
  }
  else {
    puVar10 = &DAT_00241b40 + (cVar8 * 0x14 + (int)cVar8) * 0x10;
    fVar15 = (float)param_1[0x32];
  }
  fVar12 = ABS(fVar15);
  iVar2 = *(int *)(puVar10 + 0xc4);
  if ((*(char *)(*(int *)(pcVar3 + 0x6f0) + 0x80) != '\0') ||
     (*(char *)(*(int *)(pcVar3 + 0x6f0) + 0x1b0) != '\0')) {
    lVar4 = FUN_00166b30(*(undefined4 *)(puVar10 + 0x10));
    if (lVar4 == 0) {
      pcVar3 = (char *)*param_1;
    }
    else {
      iVar1 = *param_1;
      cVar8 = *(char *)(*(int *)(iVar1 + 0x6f0) + 0x1b0);
      cVar9 = *(char *)(*(int *)(iVar1 + 0x6f0) + 0x80);
      if (cVar8 < cVar9) {
        cVar8 = cVar9;
      }
      auVar20._0_8_ = FUN_00115998(iVar1 + 0x30,*(undefined8 *)(iVar1 + 0x650));
      auVar20._8_8_ = extraout_v0_udw;
      uStack_60 = (undefined4)auVar20._0_8_;
      uStack_5c = (undefined4)((ulong)auVar20._0_8_ >> 0x20);
      uStack_58 = (undefined4)extraout_v0_udw;
      uStack_54 = (undefined4)((ulong)extraout_v0_udw >> 0x20);
      if (cVar8 == '\0') {
        fVar19 = 0.0;
        fVar15 = 0.0;
      }
      else {
        auVar20 = _por(in_zero_qw,auVar20);
        fVar15 = (float)FUN_001151d8(auVar20._0_8_);
        if (fVar15 <= 2.0) {
          fVar15 = 0.0;
          fVar19 = 0.39999998;
        }
        else {
          uVar5 = FUN_00115110();
          uStack_60 = (undefined4)uVar5;
          uStack_5c = (undefined4)((ulong)uVar5 >> 0x20);
          uStack_58 = (undefined4)extraout_v0_udw_00;
          uStack_54 = (undefined4)((ulong)extraout_v0_udw_00 >> 0x20);
          fVar19 = (float)FUN_00114c58(&uStack_60);
          fVar11 = (float)FUN_001c9f28(*(undefined4 *)(puVar10 + 0x44),
                                       *(undefined4 *)(puVar10 + 0xb8));
          fVar15 = -1.0;
          fVar11 = (fVar19 * 0.54999995) / fVar11;
          if (-1.0 <= fVar11) {
            fVar15 = (float)((int)fVar11 * (uint)(fVar11 < 1.0) | (uint)(fVar11 >= 1.0) * 0x3f800000
                            );
          }
          fVar19 = (*(float *)(*(int *)(*(int *)(*param_1 + 0x6f0) + 0x120) + 0x10c) +
                   *(float *)(*(int *)(*(int *)(*param_1 + 0x6f0) + 0x250) + 0x10c)) * 0.5;
          fVar19 = (float)((int)fVar19 * (uint)(0.39999998 < fVar19) |
                          (uint)(0.39999998 >= fVar19) * (int)0.39999998);
        }
      }
      uVar6 = FUN_00166a40(*(undefined4 *)(puVar10 + 0x10));
      if (uVar6 < 5) {
        if (uVar6 < 2) {
          pcVar3 = (char *)*param_1;
        }
        else {
          if (*(int *)(iRam002904ec + 0xc) == 3) {
            return;
          }
          fVar11 = (float)FUN_00166c20(*(undefined4 *)(puVar10 + 0x10));
          uVar17 = 0;
          fVar19 = fVar19 * fVar11 * 1.4;
          if (0.0 <= fVar19) {
            uVar17 = (int)fVar19 * (uint)(fVar19 < 1.0) | (uint)(fVar19 >= 1.0) * 0x3f800000;
          }
          uVar18 = 0xbf800000;
          if (-1.0 <= fVar15) {
            uVar18 = (int)fVar15 * (uint)(fVar15 < 1.0) | (uint)(fVar15 >= 1.0) * 0x3f800000;
          }
          FUN_00108958(uVar18,uVar17,0x3f400000,*(undefined4 *)(puVar10 + 0x10));
          pcVar3 = (char *)*param_1;
        }
      }
      else {
        pcVar3 = (char *)*param_1;
      }
    }
    fVar15 = (float)param_1[0x32];
  }
  fVar19 = 0.0;
  if (2.0 < ABS(fVar15)) {
    iVar1 = *(int *)(pcVar3 + 0x6f0);
    iVar7 = 3;
    do {
      iVar7 = iVar7 + -1;
      if (*(char *)(iVar1 + 0x80) != '\0') {
        fVar15 = *(float *)(*(int *)(iVar1 + 0x120) + 0x100);
        fVar19 = (float)((int)fVar15 * (uint)(fVar19 < fVar15) |
                        (int)fVar19 * (uint)(fVar19 >= fVar15));
      }
      iVar1 = iVar1 + 0x130;
    } while (-1 < iVar7);
  }
  if (50.0 < fVar19) {
    iVar1 = *(int *)(pcVar3 + 0x6f0);
    fVar19 = 0.0;
    fVar15 = 0.0;
    if (*(char *)(iVar1 + 0x80) == '\0') {
      iVar7 = *(int *)(iVar1 + 0x120);
    }
    else {
      iVar7 = *(int *)(iVar1 + 0x120);
      fVar15 = *(float *)(iVar7 + 0xf0);
    }
    if (*(char *)(iVar1 + 0x1b0) != '\0') {
      fVar19 = -*(float *)(*(int *)(iVar1 + 0x250) + 0xf0);
    }
    fVar16 = *(float *)(iVar7 + 0x100);
    fVar13 = *(float *)(*(int *)(iVar1 + 0x380) + 0x100);
    fVar11 = *(float *)(*(int *)(iVar1 + 0x4b0) + 0x100);
    fVar14 = *(float *)(*(int *)(iVar1 + 0x250) + 0x100);
    fVar13 = (float)((int)fVar13 * (uint)(fVar16 < fVar13) | (int)fVar16 * (uint)(fVar16 >= fVar13))
    ;
    fVar11 = (float)((int)fVar11 * (uint)(fVar14 < fVar11) | (int)fVar14 * (uint)(fVar14 >= fVar11))
    ;
    if (1.0 < ABS(*(float *)(puVar10 + 0x44))) {
      FUN_001c8f10(fVar15 * (fVar13 + fVar13),fVar19 * (fVar11 + fVar11));
      pcVar3 = (char *)*param_1;
    }
    iVar1 = *(int *)(pcVar3 + 0x6f0);
  }
  else {
    iVar1 = *(int *)(pcVar3 + 0x6f0);
  }
  fVar15 = 0.0;
  if (*(char *)(iVar1 + 0x80) == '\0') {
    iVar1 = *(int *)(pcVar3 + 0x6f0);
  }
  else {
    iVar1 = FUN_001db0a8(*(undefined1 *)(iVar1 + 6));
    fVar15 = *(float *)(iVar1 + 4);
    iVar1 = *(int *)(*param_1 + 0x6f0);
  }
  if (*(char *)(iVar1 + 0x1b0) != '\0') {
    iVar1 = FUN_001db0a8(*(undefined1 *)(iVar1 + 0x136));
    fVar15 = fVar15 - *(float *)(iVar1 + 4);
  }
  fVar15 = -(fVar15 * (fVar12 / 100.0));
  if (0.01 < ABS(fVar15)) {
    FUN_001c8f10(fVar15,fVar15);
    cVar8 = *(char *)((int)param_1 + 0x11);
  }
  else {
    cVar8 = *(char *)((int)param_1 + 0x11);
  }
  if (cVar8 == '\0') {
    auVar20 = _qmtc2(param_1[0x1d]);
    _vcallms(0x268);
    auVar20 = _qmfc2(auVar20._0_4_);
    fVar15 = ((float)param_1[0x1c] / *(float *)(iVar2 + 0x2c)) * auVar20._0_4_;
    if (0.25 < ABS(fVar15)) {
      FUN_001c8f10(fVar15,fVar15);
      iVar2 = *param_1;
    }
    else {
      iVar2 = *param_1;
    }
  }
  else {
    iVar2 = *param_1;
  }
  fVar12 = 0.0;
  iVar1 = *(int *)(iVar2 + 0x6f0);
  fVar15 = 0.0;
  if (*(char *)(iVar1 + 0x80) != '\0') {
    fVar15 = ABS(*(float *)(*(int *)(iVar1 + 0x120) + 0x114));
    if (ABS(*(float *)(iVar1 + 0x104)) < 0.0001) {
      if (fVar15 < FLOAT_002901c4 * 0.5) {
        fVar15 = 0.0;
      }
      fVar15 = fVar15 * -20.0;
    }
    else {
      fVar15 = fVar15 * -15.0;
    }
    iVar1 = *(int *)(iVar2 + 0x6f0);
  }
  if (*(char *)(iVar1 + 0x1b0) == '\0') {
    iVar2 = *(int *)(iVar2 + 0x6f0);
  }
  else {
    fVar12 = ABS(*(float *)(*(int *)(iVar1 + 0x250) + 0x114));
    if (ABS(*(float *)(iVar1 + 0x234)) < 0.0001) {
      if (fVar12 < FLOAT_002901c4 * 0.5) {
        fVar12 = 0.0;
      }
      fVar12 = fVar12 * 20.0;
    }
    else {
      fVar12 = fVar12 * 15.0;
    }
    iVar2 = *(int *)(iVar2 + 0x6f0);
  }
  pcVar3 = (char *)FUN_001db0a8(*(undefined1 *)(iVar2 + 6));
  cVar8 = *pcVar3;
  cVar9 = pcVar3[1];
  pcVar3 = (char *)FUN_001db0a8(*(undefined1 *)(*(int *)(*param_1 + 0x6f0) + 0x136));
  if (pcVar3[1] < cVar9) {
    cVar9 = pcVar3[1];
  }
  if (cVar9 != '\0') {
    iVar2 = *(int *)(*(int *)(*param_1 + 8) + 4);
    fVar19 = ABS(*(float *)(iVar2 + 0x114) /
                 *(float *)(*(short *)(iVar2 + 0x16) * 4 + *(int *)(iRam00290534 + 0x34))) * 3.0;
    if (0.0 <= fVar19) {
      fVar19 = (float)((int)fVar19 * (uint)(fVar19 < 1.0) | (uint)(fVar19 >= 1.0) * 0x3f800000);
    }
    else {
      fVar19 = 0.0;
    }
    fVar12 = fVar12 * fVar19;
    fVar15 = fVar15 * fVar19;
  }
  if (*pcVar3 == '\x06' || cVar8 == '\x06') {
    FUN_001c8f10(fVar15,fVar12);
  }
  else {
    FUN_001c8f10(fVar15,fVar12);
  }
  return;
}

