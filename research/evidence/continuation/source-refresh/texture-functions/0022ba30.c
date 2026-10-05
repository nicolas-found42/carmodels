
/* source file (direct reference to its __FILE__ string, not proof of authorship):
   ../modules4/3d/ps2/3dobjtex.c */

uint FUN_0022ba30(undefined8 param_1,int *param_2)

{
  byte bVar1;
  int iVar2;
  int iVar3;
  int iVar4;
  char cVar5;
  undefined4 *puVar6;
  undefined4 uVar7;
  int *piVar8;
  uint uVar9;
  uint uVar10;
  undefined8 uVar11;
  int iVar12;
  uint *puVar13;
  undefined4 *puVar14;
  int iVar15;
  uint *puVar16;
  int iVar17;
  char *pcVar18;
  uint *puVar19;
  int iVar20;
  uint uVar21;
  int iVar22;
  uint uVar23;
  int iVar24;
  int iVar25;
  
  iVar24 = (int)param_1;
  *(int **)(iVar24 + 0x100) = param_2;
  iVar2 = *param_2;
  iVar3 = param_2[1];
  *(int **)(iVar24 + 0xfc) = param_2 + 3;
  iVar4 = param_2[2];
  iVar15 = iVar2 + iVar3 + iVar4;
  *(int *)(iVar24 + 0xe0) = iVar15;
  uVar21 = (int)(param_2 + 3) + iVar15 * 0xc + 0xf & 0xfffffff0;
  iVar15 = FUN_0010d020(iVar15 * 4);
  *(int *)(iVar24 + 0xf8) = iVar15;
  iVar20 = 0;
  if (0 < iVar2) {
    iVar22 = *(int *)(iVar24 + 0xfc);
    iVar17 = 0;
    iVar25 = iVar2;
    do {
      iVar12 = iVar20 * 4;
      iVar20 = iVar20 + 1;
      *(uint *)(iVar12 + iVar15) = uVar21;
      uVar21 = uVar21 + 0x400;
      *(undefined4 *)(iVar17 + iVar22 + 8) = 0;
      iVar25 = iVar25 + -1;
      iVar15 = *(int *)(iVar24 + 0xf8);
      iVar22 = *(int *)(iVar24 + 0xfc);
      uVar7 = *(undefined4 *)(iVar12 + iVar15);
      puVar6 = (undefined4 *)(iVar17 + iVar22);
      puVar6[1] = 0;
      iVar17 = iVar17 + 0xc;
      *puVar6 = uVar7;
    } while (iVar25 != 0);
  }
  if (0 < iVar3) {
    iVar15 = *(int *)(iVar24 + 0xf8);
    iVar22 = *(int *)(iVar24 + 0xfc);
    iVar17 = iVar20 * 0xc;
    iVar25 = iVar3;
    do {
      iVar12 = iVar20 * 4;
      iVar20 = iVar20 + 1;
      *(uint *)(iVar12 + iVar15) = uVar21;
      uVar21 = uVar21 + 0x40;
      *(undefined4 *)(iVar17 + iVar22 + 8) = 0;
      iVar25 = iVar25 + -1;
      iVar15 = *(int *)(iVar24 + 0xf8);
      iVar22 = *(int *)(iVar24 + 0xfc);
      uVar7 = *(undefined4 *)(iVar12 + iVar15);
      puVar6 = (undefined4 *)(iVar17 + iVar22);
      puVar6[1] = 1;
      iVar17 = iVar17 + 0xc;
      *puVar6 = uVar7;
    } while (iVar25 != 0);
  }
  if (iVar4 < 1) {
    iVar15 = uVar21 + 4;
  }
  else {
    iVar15 = *(int *)(iVar24 + 0xf8);
    iVar22 = *(int *)(iVar24 + 0xfc);
    iVar17 = iVar20 * 0xc;
    iVar25 = iVar4;
    do {
      uVar9 = uVar21;
      iVar12 = iVar20 * 4;
      iVar20 = iVar20 + 1;
      *(uint *)(iVar12 + iVar15) = uVar9;
      *(undefined4 *)(iVar17 + iVar22 + 8) = 0;
      iVar25 = iVar25 + -1;
      iVar15 = *(int *)(iVar24 + 0xf8);
      iVar22 = *(int *)(iVar24 + 0xfc);
      uVar7 = *(undefined4 *)(iVar12 + iVar15);
      puVar6 = (undefined4 *)(iVar17 + iVar22);
      puVar6[1] = 0;
      iVar17 = iVar17 + 0xc;
      *puVar6 = uVar7;
      uVar21 = uVar9 + 0x400;
    } while (iVar25 != 0);
    iVar15 = uVar9 + 0x404;
  }
  uVar21 = 0;
  iVar20 = *(int *)(iVar15 + -4);
  puVar6 = (undefined4 *)(iVar15 + 4);
  *(int *)(iVar24 + 0xe4) = iVar20;
  uVar7 = FUN_0010d020(iVar20 << 2);
  *(undefined4 *)(iVar24 + 0xec) = uVar7;
  uVar7 = FUN_0010d020(*(int *)(iVar24 + 0xe4) << 3);
  *(undefined4 *)(iVar24 + 0xf4) = uVar7;
  uVar7 = FUN_0010d020(*(int *)(iVar24 + 0xe4) << 2);
  *(undefined4 *)(iVar24 + 0x104) = uVar7;
  uVar7 = FUN_0010d020(*(int *)(iVar24 + 0xe4) * 0xc);
  *(undefined4 *)(iVar24 + 0x108) = uVar7;
  uVar11 = FUN_0010d020(0x400);
  *(int *)(iVar24 + 0x10c) = (int)uVar11;
  FUN_0020c7fc(uVar11,0,0x400);
  if (0 < *(int *)(iVar24 + 0xe4)) {
    iVar15 = *(int *)(iVar24 + 0xf4);
    iVar20 = 0;
    do {
      iVar25 = uVar21 * 4;
      *(undefined4 *)(uVar21 * 8 + iVar15) = *puVar6;
      iVar22 = 0;
      iVar15 = puVar6[1];
      piVar8 = (int *)(iVar25 + *(int *)(iVar24 + 0x104));
      *piVar8 = (int)(puVar6 + 2);
      puVar6 = (undefined4 *)((int)(puVar6 + 2) + iVar15);
      if (0 < iVar15) {
        iVar17 = *piVar8;
        while( true ) {
          pcVar18 = (char *)(iVar17 + iVar22);
          iVar22 = iVar22 + 1;
          cVar5 = *pcVar18;
          if ((*(byte *)((int)&PTR_DAT_0028d091 + (int)cVar5) & 2) != 0) {
            cVar5 = cVar5 + -0x20;
          }
          *pcVar18 = cVar5;
          if (iVar15 <= iVar22) break;
          iVar17 = *(int *)(iVar25 + *(int *)(iVar24 + 0x104));
        }
        piVar8 = (int *)(iVar25 + *(int *)(iVar24 + 0x104));
      }
      uVar9 = FUN_0020e10c(*piVar8);
      iVar15 = *(int *)(iVar24 + 0x104);
      for (uVar23 = 0; uVar10 = FUN_0020e10c(*(undefined4 *)(iVar25 + iVar15)), uVar23 < uVar10;
          uVar23 = uVar23 + 1) {
        iVar15 = *(int *)(iVar24 + 0x104);
        uVar9 = (uVar9 + (int)*(char *)(*(int *)(iVar25 + iVar15) + uVar23)) * 2;
      }
      puVar16 = (uint *)((uVar9 & 0xff) * 4 + *(int *)(iVar24 + 0x10c));
      iVar15 = *(int *)(iVar24 + 0xf4);
      uVar23 = *puVar16;
      puVar13 = (uint *)(iVar20 + *(int *)(iVar24 + 0x108));
      *puVar13 = uVar9;
      puVar19 = (uint *)(uVar21 * 8 + iVar15);
      puVar13[2] = uVar23;
      puVar13[1] = uVar21;
      uVar9 = *puVar19;
      *puVar16 = *(int *)(iVar24 + 0x108) + iVar20;
      if ((uVar9 & 1) == 0) {
        iVar22 = *(int *)(iVar24 + 0xec);
        uVar10 = (int)puVar6 + 0xfU & 0xfffffff0;
        *(uint *)(iVar25 + iVar22) = uVar10;
        puVar19[1] = uVar10;
        uVar9 = *(uint *)(iVar25 + iVar22);
        uVar23 = (uint)*(byte *)(uVar9 + 0x35);
        puVar6 = (undefined4 *)(uVar10 + 0x40);
        if (uVar23 != 0) {
          *(undefined4 **)(uVar9 + 0x2c) = puVar6;
          for (; uVar23 != 0; uVar23 = uVar23 - 1) {
            puVar6 = puVar6 + 4;
          }
        }
        piVar8 = *(int **)(iVar25 + iVar22);
        bVar1 = *(byte *)(piVar8 + 0xd);
        if (bVar1 == 0) {
          puVar14 = *(undefined4 **)(iVar25 + iVar22);
        }
        else {
          if ((2 < bVar1) && (bVar1 < 5)) {
            *piVar8 = *(int *)(iVar24 + 0xfc) + *piVar8 * 0xc;
            goto LAB_0022be60;
          }
          puVar14 = *(undefined4 **)(iVar25 + iVar22);
        }
        *puVar14 = 0;
      }
      else {
        *(undefined4 *)(iVar25 + *(int *)(iVar24 + 0xec)) = 0;
        puVar19[1] = 0;
      }
LAB_0022be60:
      iVar22 = *(int *)(iVar24 + 0xe4);
      uVar21 = uVar21 + 1;
      iVar20 = iVar20 + 0xc;
    } while ((int)uVar21 < iVar22);
    iVar15 = 0;
    if (0 < iVar22) {
      iVar20 = 0;
      do {
        if ((*(uint *)(iVar15 * 8 + *(int *)(iVar24 + 0xf4)) & 1) == 0) {
          iVar22 = *(int *)(iVar24 + 0xec);
          iVar25 = 0;
          piVar8 = (int *)(iVar20 + iVar22);
          iVar12 = 1 << ((uint)((ulong)(*(long *)(*piVar8 + 0x38) << 0x11) >> 0x20) & 0xf);
          iVar17 = 1 << ((uint)((ulong)(*(long *)(*piVar8 + 0x38) << 0xd) >> 0x20) & 0xf);
          do {
            uVar21 = (int)puVar6 + 0xfU & 0xfffffff0;
            if (iVar25 == 0) {
              *(uint *)(*(int *)(iVar20 + iVar22) + 0x28) = uVar21;
            }
            else {
              *(uint *)(*(int *)(*piVar8 + 0x2c) + iVar25 * 0x10 + -8) = uVar21;
            }
            bVar1 = *(byte *)(*piVar8 + 0x34);
            if (bVar1 == 2) {
              puVar6 = (undefined4 *)(uVar21 + iVar12 * iVar17 * 2);
            }
            else if (bVar1 < 3) {
              puVar6 = (undefined4 *)(uVar21 + iVar12 * iVar17 * 4);
              if (bVar1 != 1) {
LAB_0022bfa0:
                    /* WARNING: Subroutine does not return */
                FUN_00105888(0x252fc0,0x1ab,0x252fe0);
              }
            }
            else if (bVar1 == 3) {
              puVar6 = (undefined4 *)(iVar12 * iVar17 + uVar21);
            }
            else {
              if (bVar1 != 4) goto LAB_0022bfa0;
              puVar6 = (undefined4 *)(uVar21 + (iVar12 * iVar17) / 2);
            }
            iVar25 = iVar25 + 1;
            iVar12 = iVar12 >> 1;
            iVar17 = iVar17 >> 1;
          } while (iVar25 <= (int)(uint)*(byte *)(*(int *)(iVar20 + iVar22) + 0x35));
          FUN_0022c660(*(undefined4 *)(iVar20 + iVar22));
          iVar22 = *(int *)(iVar24 + 0xe4);
        }
        iVar15 = iVar15 + 1;
        iVar20 = iVar20 + 4;
      } while (iVar15 < iVar22);
    }
  }
  FUN_0022c048(param_1,iVar2,iVar3,iVar4);
  return (int)puVar6 + 0xfU & 0xfffffff0;
}

