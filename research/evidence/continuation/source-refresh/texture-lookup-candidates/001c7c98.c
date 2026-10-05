
void FUN_001c7c98(undefined8 param_1)

{
  char cVar1;
  int iVar2;
  char *pcVar3;
  bool bVar4;
  bool bVar5;
  float fVar6;
  int iVar7;
  long lVar8;
  int iVar9;
  int iVar10;
  ulong uVar11;
  int iVar12;
  int *piVar13;
  undefined *puVar14;
  float fVar15;
  uint uVar16;
  float fVar17;
  float fVar18;
  float fVar19;
  undefined1 auVar20 [16];
  undefined1 auVar21 [16];
  undefined1 auVar22 [16];
  undefined1 auVar23 [16];
  
  fVar6 = FLOAT_00290264;
  piVar13 = (int *)param_1;
  cVar1 = *(char *)*piVar13;
  if (cVar1 < '\0') {
    puVar14 = (undefined *)0x0;
    fVar15 = (float)piVar13[0x32];
  }
  else {
    puVar14 = &DAT_00241b40 + (cVar1 * 0x14 + (int)cVar1) * 0x10;
    fVar15 = (float)piVar13[0x32];
  }
  fVar19 = 4.0;
  fVar15 = (1.0 - ABS(fVar15) * 0.01) * FLOAT_00290264;
  *(ulong *)(piVar13 + 0x38) = *(ulong *)(piVar13 + 0x38) & 0xfffffffffffffcff;
  if (4.0 <= fVar15) {
    fVar19 = (float)((int)fVar15 * (uint)(fVar15 < fVar6) | (int)fVar6 * (uint)(fVar15 >= fVar6));
  }
  lVar8 = FUN_001ca568(param_1);
  if (lVar8 == 0) {
    bVar4 = false;
    lVar8 = FUN_001ca500(param_1);
    if (lVar8 == 1) {
      bVar4 = true;
    }
  }
  else {
    bVar4 = true;
  }
  lVar8 = FUN_001ca5a0(param_1);
  if (lVar8 == 0) {
    bVar5 = false;
    lVar8 = FUN_001ca500(param_1);
    if (lVar8 != 1) {
      iVar9 = *piVar13;
      goto LAB_001c7da8;
    }
  }
  bVar5 = true;
  iVar9 = *piVar13;
LAB_001c7da8:
  if ((*(int *)(*(int *)(*(int *)(iVar9 + 8) + 4) + 300) == 1) &&
     (bVar4 = false, *(int *)(*(int *)(puVar14 + 0xb0) + 0x140) == 5)) {
    iVar7 = FUN_00161410();
    iVar9 = *piVar13;
    if ((*(int *)((iVar7 + 0x1fU & 0xfffffff0) + 0x40) == 5) &&
       (0.0 < *(float *)(*(int *)(*(int *)(iVar9 + 8) + 4) + 0x70))) {
      bVar4 = true;
    }
  }
  iVar7 = 0;
  do {
    iVar2 = *(int *)(puVar14 + iVar7 * 4 + 0xcc);
    iVar12 = iVar7 * 0x130;
    iVar10 = iVar12 + *(int *)(iVar9 + 0x6f0);
    auVar21 = _lqc2(*(undefined1 (*) [16])(iVar9 + 0x650));
    auVar23 = _lqc2(*(undefined1 (*) [16])(*(int *)(iVar10 + 0x120) + 0x30));
    auVar22 = _lqc2(*(undefined1 (*) [16])(iVar9 + 0x5a0));
    auVar20 = _lqc2(*(undefined1 (*) [16])(iVar10 + 0x60));
    _vopmula(auVar20,auVar22);
    auVar20 = _vopmsub(auVar22,auVar20);
    auVar20 = _vsub(auVar20,auVar20);
    auVar20 = _vadd(auVar21,auVar20);
    auVar20 = _vmul(auVar20,auVar23);
    auVar20 = _vaddbc(auVar20,auVar20);
    fVar18 = *(float *)(iVar2 + 0x28) * *(float *)(*(int *)(iVar10 + 0x120) + 0xec) * 0.10471974;
    auVar20 = _vaddbc(auVar20,auVar20);
    auVar20 = _qmfc2(auVar20._0_4_);
    fVar15 = auVar20._0_4_;
    *(undefined1 *)(iVar10 + 9) = 0;
    if (((fVar18 <= 0.0) || (fVar15 <= 0.0)) || (fVar18 <= fVar15)) {
      if (((fVar18 <= 0.0) || (fVar15 <= 1.0)) || (fVar15 <= fVar18)) {
        if ((fVar18 <= 0.0) || (0.0 <= fVar15)) {
          if (((0.0 <= fVar18) || (-5.0 <= fVar15)) || (fVar18 <= fVar15)) {
            if (((fVar18 < 0.0) && (fVar15 < 0.0)) && (fVar18 < fVar15)) {
              iVar9 = iVar7 * 0x130 + *(int *)(*piVar13 + 0x6f0);
              if ((fVar19 < *(float *)(*(int *)(iVar9 + 0x120) + 0x100)) &&
                 (*(undefined1 *)(iVar9 + 9) = 3, bVar4)) {
                iVar10 = 0x100;
                fVar17 = *(float *)(iVar2 + 0x3c);
                iVar9 = *(int *)(iVar7 * 0x130 + *(int *)(*piVar13 + 0x6f0) + 0x120);
                fVar18 = *(float *)(iVar9 + 0xec);
                fVar15 = fVar15 + fVar19 * 0.01 * fVar15;
                goto LAB_001c8204;
              }
            }
          }
          else {
            iVar9 = iVar7 * 0x130 + *(int *)(*piVar13 + 0x6f0);
            if (((fVar6 < *(float *)(*(int *)(iVar9 + 0x120) + 0x100)) &&
                (*(undefined1 *)(iVar9 + 9) = 3, bVar5)) &&
               ((iVar7 < 2 || ((float)piVar13[0xe] <= 0.0)))) {
              uVar11 = 0x200;
              iVar9 = *(int *)(iVar7 * 0x130 + *(int *)(*piVar13 + 0x6f0) + 0x120);
              fVar18 = *(float *)(iVar9 + 0xec);
              fVar15 = (fVar15 - fVar6 * 0.01 * fVar15) * *(float *)(iVar2 + 0x3c) * 9.549295;
              uVar16 = (int)fVar15 * (uint)(fVar15 < fVar18) |
                       (int)fVar18 * (uint)(fVar15 >= fVar18);
              goto LAB_001c8210;
            }
          }
        }
        else {
          iVar9 = iVar7 * 0x130 + *(int *)(*piVar13 + 0x6f0);
          if (fVar19 < *(float *)(*(int *)(iVar9 + 0x120) + 0x100)) {
            *(undefined1 *)(iVar9 + 9) = 2;
            pcVar3 = *(char **)(iVar7 * 0x130 + *(int *)(*piVar13 + 0x6f0) + 0x120);
            if ((*pcVar3 != '\0') && (bVar4)) {
              fVar18 = *(float *)(pcVar3 + 0xec);
              fVar15 = (fVar15 - fVar19 * 0.01 * fVar15) * *(float *)(iVar2 + 0x3c) * 9.549295;
              *(uint *)(pcVar3 + 0xec) =
                   (int)fVar15 * (uint)(fVar15 < fVar18) | (int)fVar18 * (uint)(fVar15 >= fVar18);
              uVar11 = *(ulong *)(piVar13 + 0x38) | 0x100;
              goto LAB_001c821c;
            }
          }
        }
      }
      else {
        iVar9 = iVar7 * 0x130 + *(int *)(*piVar13 + 0x6f0);
        if (((fVar6 < *(float *)(*(int *)(iVar9 + 0x120) + 0x100)) &&
            (*(undefined1 *)(iVar9 + 9) = 3, bVar5)) &&
           ((iVar7 < 2 || ((float)piVar13[0xe] <= 0.0)))) {
          iVar10 = 0x200;
          fVar17 = *(float *)(iVar2 + 0x3c);
          iVar9 = *(int *)(iVar7 * 0x130 + *(int *)(*piVar13 + 0x6f0) + 0x120);
          fVar18 = *(float *)(iVar9 + 0xec);
          fVar15 = (1.0 - fVar6 * 0.01) * fVar15;
LAB_001c8204:
          uVar11 = (ulong)iVar10;
          fVar15 = fVar15 * fVar17 * 9.549295;
          uVar16 = (int)fVar15 * (uint)(fVar18 < fVar15) | (int)fVar18 * (uint)(fVar18 >= fVar15);
          goto LAB_001c8210;
        }
      }
    }
    else {
      iVar9 = iVar12 + *(int *)(*piVar13 + 0x6f0);
      pcVar3 = *(char **)(iVar9 + 0x120);
      if (((fVar19 < *(float *)(pcVar3 + 0x100)) && (*pcVar3 != '\0')) &&
         (*(undefined1 *)(iVar9 + 9) = 2, bVar4)) {
        uVar11 = 0x100;
        iVar9 = *(int *)(iVar12 + *(int *)(*piVar13 + 0x6f0) + 0x120);
        fVar18 = *(float *)(iVar9 + 0xec);
        fVar15 = (fVar19 * 0.01 * fVar15 + fVar15) * *(float *)(iVar2 + 0x3c) * 9.549295;
        uVar16 = (int)fVar15 * (uint)(fVar15 < fVar18) | (int)fVar18 * (uint)(fVar15 >= fVar18);
LAB_001c8210:
        *(uint *)(iVar9 + 0xec) = uVar16;
        uVar11 = *(ulong *)(piVar13 + 0x38) | uVar11;
LAB_001c821c:
        *(ulong *)(piVar13 + 0x38) = uVar11;
      }
    }
    iVar7 = iVar7 + 1;
    if (3 < iVar7) {
      return;
    }
    iVar9 = *piVar13;
  } while( true );
}

