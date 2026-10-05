
void FUN_00143e18(int param_1,int param_2,ulong param_3,undefined8 param_4,ulong param_5,
                 ulong param_6,ulong param_7,ulong param_8)

{
  uint uVar1;
  undefined4 uVar2;
  ulong *puVar3;
  undefined8 *puVar4;
  ulong *puVar5;
  ulong uVar6;
  uint uVar7;
  ulong *puVar8;
  undefined8 *puVar9;
  ulong uVar10;
  undefined8 *puVar11;
  uint uVar12;
  ulong *puVar13;
  undefined8 uVar14;
  int iVar15;
  ulong uVar16;
  undefined8 uVar17;
  undefined8 uVar18;
  ulong uVar19;
  
  uVar16 = (ulong)iRam0028f57c;
  switch(param_1 + -1) {
  case 0:
  case 1:
    uVar16 = (ulong)iRam0028f57c;
    break;
  case 2:
    uVar16 = (ulong)iRam0028f590;
    break;
  case 3:
    uVar16 = (ulong)iRam0028f580;
    break;
  case 4:
    uVar16 = (ulong)iRam0028f584;
    break;
  case 5:
    uVar16 = (ulong)iRam0028f594;
    break;
  case 6:
    uVar16 = (ulong)iRam0028f588;
    break;
  case 7:
    uVar16 = (ulong)iRam0028f58c;
  }
  iVar15 = (int)uVar16;
  if (uVar16 != 0) {
    param_3 = (ulong)(int)*(uint *)(param_2 + 4);
    uVar1 = *(uint *)(iVar15 + 4);
    uVar10 = (ulong)(int)uVar1;
    uVar6 = (ulong)(int)(uVar1 + 0x100);
    if (((uVar1 | *(uint *)(param_2 + 4)) & 7) == 0) {
      do {
        puVar8 = (ulong *)uVar10;
        param_5 = *puVar8;
        param_6 = puVar8[1];
        uVar10 = puVar8[2];
        param_8 = puVar8[3];
        puVar13 = (ulong *)param_3;
        *puVar13 = param_5;
        puVar13[1] = param_6;
        puVar13[2] = uVar10;
        puVar13[3] = param_8;
        puVar8 = puVar8 + 4;
        uVar10 = (ulong)(int)puVar8;
        param_3 = (ulong)(int)(puVar13 + 4);
      } while (uVar10 != uVar6);
    }
    else {
      do {
        uVar7 = (uint)uVar10;
        uVar1 = uVar7 + 7 & 7;
        uVar12 = uVar7 & 7;
        param_5 = (*(long *)((uVar7 + 7) - uVar1) << (7 - uVar1) * 8 |
                  param_5 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                  *(ulong *)(uVar7 - uVar12) >> uVar12 * 8;
        uVar1 = uVar7 + 0xf & 7;
        uVar12 = uVar7 + 8 & 7;
        param_6 = (*(long *)((uVar7 + 0xf) - uVar1) << (7 - uVar1) * 8 |
                  param_6 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                  *(ulong *)((uVar7 + 8) - uVar12) >> uVar12 * 8;
        uVar1 = uVar7 + 0x17 & 7;
        uVar12 = uVar7 + 0x10 & 7;
        param_7 = (*(long *)((uVar7 + 0x17) - uVar1) << (7 - uVar1) * 8 |
                  param_7 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                  *(ulong *)((uVar7 + 0x10) - uVar12) >> uVar12 * 8;
        uVar1 = uVar7 + 0x1f & 7;
        uVar12 = uVar7 + 0x18 & 7;
        param_8 = (*(long *)((uVar7 + 0x1f) - uVar1) << (7 - uVar1) * 8 |
                  param_8 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                  *(ulong *)((uVar7 + 0x18) - uVar12) >> uVar12 * 8;
        uVar12 = (uint)param_3;
        uVar1 = uVar12 + 7 & 7;
        puVar8 = (ulong *)((uVar12 + 7) - uVar1);
        *puVar8 = *puVar8 & -1L << (uVar1 + 1) * 8 | param_5 >> (7 - uVar1) * 8;
        uVar1 = uVar12 & 7;
        *(ulong *)(uVar12 - uVar1) =
             param_5 << uVar1 * 8 |
             *(ulong *)(uVar12 - uVar1) & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        uVar1 = uVar12 + 0xf & 7;
        puVar8 = (ulong *)((uVar12 + 0xf) - uVar1);
        *puVar8 = *puVar8 & -1L << (uVar1 + 1) * 8 | param_6 >> (7 - uVar1) * 8;
        uVar1 = uVar12 + 8 & 7;
        puVar8 = (ulong *)((uVar12 + 8) - uVar1);
        *puVar8 = param_6 << uVar1 * 8 | *puVar8 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        uVar1 = uVar12 + 0x17 & 7;
        puVar8 = (ulong *)((uVar12 + 0x17) - uVar1);
        *puVar8 = *puVar8 & -1L << (uVar1 + 1) * 8 | param_7 >> (7 - uVar1) * 8;
        uVar1 = uVar12 + 0x10 & 7;
        puVar8 = (ulong *)((uVar12 + 0x10) - uVar1);
        *puVar8 = param_7 << uVar1 * 8 | *puVar8 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        uVar1 = uVar12 + 0x1f & 7;
        puVar8 = (ulong *)((uVar12 + 0x1f) - uVar1);
        *puVar8 = *puVar8 & -1L << (uVar1 + 1) * 8 | param_8 >> (7 - uVar1) * 8;
        uVar1 = uVar12 + 0x18 & 7;
        puVar8 = (ulong *)((uVar12 + 0x18) - uVar1);
        *puVar8 = param_8 << uVar1 * 8 | *puVar8 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        puVar8 = (ulong *)(uVar7 + 0x20);
        uVar10 = (ulong)(int)puVar8;
        param_3 = (ulong)(int)(uVar12 + 0x20);
      } while (uVar10 != uVar6);
    }
    uVar1 = (int)puVar8 + 7U & 7;
    uVar12 = (uint)puVar8 & 7;
    uVar6 = (*(long *)(((int)puVar8 + 7U) - uVar1) << (7 - uVar1) * 8 |
            uVar6 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
            *(ulong *)((int)puVar8 - uVar12) >> uVar12 * 8;
    uVar12 = (uint)param_3;
    uVar1 = uVar12 + 7 & 7;
    puVar8 = (ulong *)((uVar12 + 7) - uVar1);
    *puVar8 = *puVar8 & -1L << (uVar1 + 1) * 8 | uVar6 >> (7 - uVar1) * 8;
    uVar1 = uVar12 & 7;
    *(ulong *)(uVar12 - uVar1) =
         uVar6 << uVar1 * 8 | *(ulong *)(uVar12 - uVar1) & 0xffffffffffffffffU >> (8 - uVar1) * 8;
  }
  switch(param_1 + -1) {
  case 0:
    goto switchD_00143f50_caseD_0;
  case 1:
    break;
  case 2:
    *(undefined4 *)(*(int *)(param_2 + 4) + 0x194) = 0;
    *(undefined4 *)(*(int *)(param_2 + 4) + 0x198) = 0;
    *(undefined4 *)(*(int *)(param_2 + 4) + 0x19c) = 0;
    *(undefined4 *)(*(int *)(param_2 + 4) + 0x1a0) = 0;
switchD_00143f50_caseD_0:
    if (uVar16 == 0) {
      iVar15 = *(int *)(param_2 + 4);
      goto LAB_00144488;
    }
    puVar9 = *(undefined8 **)(iVar15 + 4);
    puVar11 = *(undefined8 **)(param_2 + 4);
    puVar4 = puVar9 + 0x30;
    if ((((uint)puVar9 | (uint)puVar11) & 7) == 0) {
      do {
        uVar17 = puVar9[1];
        uVar18 = puVar9[2];
        uVar14 = puVar9[3];
        *puVar11 = *puVar9;
        puVar11[1] = uVar17;
        puVar11[2] = uVar18;
        puVar11[3] = uVar14;
        puVar9 = puVar9 + 4;
        puVar11 = puVar11 + 4;
      } while (puVar9 != puVar4);
    }
    else {
      do {
        uVar1 = (int)puVar9 + 7U & 7;
        uVar12 = (uint)puVar9 & 7;
        param_8 = (*(long *)(((int)puVar9 + 7U) - uVar1) << (7 - uVar1) * 8 |
                  param_8 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                  *(ulong *)((int)puVar9 - uVar12) >> uVar12 * 8;
        uVar1 = (int)puVar9 + 0xfU & 7;
        uVar12 = (uint)(puVar9 + 1) & 7;
        param_3 = (*(long *)(((int)puVar9 + 0xfU) - uVar1) << (7 - uVar1) * 8 |
                  param_3 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                  *(ulong *)((int)(puVar9 + 1) - uVar12) >> uVar12 * 8;
        uVar1 = (int)puVar9 + 0x17U & 7;
        uVar12 = (uint)(puVar9 + 2) & 7;
        uVar16 = (*(long *)(((int)puVar9 + 0x17U) - uVar1) << (7 - uVar1) * 8 |
                 uVar16 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                 *(ulong *)((int)(puVar9 + 2) - uVar12) >> uVar12 * 8;
        uVar1 = (int)puVar9 + 0x1fU & 7;
        uVar12 = (uint)(puVar9 + 3) & 7;
        param_5 = (*(long *)(((int)puVar9 + 0x1fU) - uVar1) << (7 - uVar1) * 8 |
                  param_5 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                  *(ulong *)((int)(puVar9 + 3) - uVar12) >> uVar12 * 8;
        uVar1 = (int)puVar11 + 7U & 7;
        puVar8 = (ulong *)(((int)puVar11 + 7U) - uVar1);
        *puVar8 = *puVar8 & -1L << (uVar1 + 1) * 8 | param_8 >> (7 - uVar1) * 8;
        uVar1 = (uint)puVar11 & 7;
        *(ulong *)((int)puVar11 - uVar1) =
             param_8 << uVar1 * 8 |
             *(ulong *)((int)puVar11 - uVar1) & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        uVar1 = (int)puVar11 + 0xfU & 7;
        puVar8 = (ulong *)(((int)puVar11 + 0xfU) - uVar1);
        *puVar8 = *puVar8 & -1L << (uVar1 + 1) * 8 | param_3 >> (7 - uVar1) * 8;
        uVar1 = (uint)(puVar11 + 1) & 7;
        puVar8 = (ulong *)((int)(puVar11 + 1) - uVar1);
        *puVar8 = param_3 << uVar1 * 8 | *puVar8 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        uVar1 = (int)puVar11 + 0x17U & 7;
        puVar8 = (ulong *)(((int)puVar11 + 0x17U) - uVar1);
        *puVar8 = *puVar8 & -1L << (uVar1 + 1) * 8 | uVar16 >> (7 - uVar1) * 8;
        uVar1 = (uint)(puVar11 + 2) & 7;
        puVar8 = (ulong *)((int)(puVar11 + 2) - uVar1);
        *puVar8 = uVar16 << uVar1 * 8 | *puVar8 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        uVar1 = (int)puVar11 + 0x1fU & 7;
        puVar8 = (ulong *)(((int)puVar11 + 0x1fU) - uVar1);
        *puVar8 = *puVar8 & -1L << (uVar1 + 1) * 8 | param_5 >> (7 - uVar1) * 8;
        uVar1 = (uint)(puVar11 + 3) & 7;
        puVar8 = (ulong *)((int)(puVar11 + 3) - uVar1);
        *puVar8 = param_5 << uVar1 * 8 | *puVar8 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        puVar9 = puVar9 + 4;
        puVar11 = puVar11 + 4;
      } while (puVar9 != puVar4);
    }
LAB_001442b4:
    uVar1 = (int)puVar9 + 7U & 7;
    uVar12 = (uint)puVar9 & 7;
    uVar16 = (*(long *)(((int)puVar9 + 7U) - uVar1) << (7 - uVar1) * 8 |
             uVar16 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
             *(ulong *)((int)puVar9 - uVar12) >> uVar12 * 8;
    uVar1 = (int)puVar9 + 0xfU & 7;
    uVar12 = (uint)(puVar9 + 1) & 7;
    uVar6 = (*(long *)(((int)puVar9 + 0xfU) - uVar1) << (7 - uVar1) * 8 |
            param_5 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
            *(ulong *)((int)(puVar9 + 1) - uVar12) >> uVar12 * 8;
    uVar2 = *(undefined4 *)(puVar9 + 2);
    uVar1 = (int)puVar11 + 7U & 7;
    puVar8 = (ulong *)(((int)puVar11 + 7U) - uVar1);
    *puVar8 = *puVar8 & -1L << (uVar1 + 1) * 8 | uVar16 >> (7 - uVar1) * 8;
    uVar1 = (uint)puVar11 & 7;
    *(ulong *)((int)puVar11 - uVar1) =
         uVar16 << uVar1 * 8 |
         *(ulong *)((int)puVar11 - uVar1) & 0xffffffffffffffffU >> (8 - uVar1) * 8;
    uVar1 = (int)puVar11 + 0xfU & 7;
    puVar8 = (ulong *)(((int)puVar11 + 0xfU) - uVar1);
    *puVar8 = *puVar8 & -1L << (uVar1 + 1) * 8 | uVar6 >> (7 - uVar1) * 8;
    uVar1 = (uint)(puVar11 + 1) & 7;
    puVar8 = (ulong *)((int)(puVar11 + 1) - uVar1);
    *puVar8 = uVar6 << uVar1 * 8 | *puVar8 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
    *(undefined4 *)(puVar11 + 2) = uVar2;
    break;
  case 3:
    if (uVar16 == 0) {
      iVar15 = *(int *)(param_2 + 4);
      goto LAB_00144488;
    }
    puVar8 = *(ulong **)(iVar15 + 4);
    puVar13 = *(ulong **)(param_2 + 4);
    puVar5 = puVar8 + 0x24;
    if ((((uint)puVar8 | (uint)puVar13) & 7) == 0) {
      do {
        param_6 = *puVar8;
        uVar10 = puVar8[1];
        uVar19 = puVar8[2];
        uVar6 = puVar8[3];
        *puVar13 = param_6;
        puVar13[1] = uVar10;
        puVar13[2] = uVar19;
        puVar13[3] = uVar6;
        puVar8 = puVar8 + 4;
        puVar13 = puVar13 + 4;
      } while (puVar8 != puVar5);
    }
    else {
      do {
        uVar1 = (int)puVar8 + 7U & 7;
        uVar12 = (uint)puVar8 & 7;
        param_8 = (*(long *)(((int)puVar8 + 7U) - uVar1) << (7 - uVar1) * 8 |
                  param_8 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                  *(ulong *)((int)puVar8 - uVar12) >> uVar12 * 8;
        uVar1 = (int)puVar8 + 0xfU & 7;
        uVar12 = (uint)(puVar8 + 1) & 7;
        param_3 = (*(long *)(((int)puVar8 + 0xfU) - uVar1) << (7 - uVar1) * 8 |
                  param_3 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                  *(ulong *)((int)(puVar8 + 1) - uVar12) >> uVar12 * 8;
        uVar1 = (int)puVar8 + 0x17U & 7;
        uVar12 = (uint)(puVar8 + 2) & 7;
        uVar16 = (*(long *)(((int)puVar8 + 0x17U) - uVar1) << (7 - uVar1) * 8 |
                 uVar16 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                 *(ulong *)((int)(puVar8 + 2) - uVar12) >> uVar12 * 8;
        uVar1 = (int)puVar8 + 0x1fU & 7;
        uVar12 = (uint)(puVar8 + 3) & 7;
        param_5 = (*(long *)(((int)puVar8 + 0x1fU) - uVar1) << (7 - uVar1) * 8 |
                  param_5 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                  *(ulong *)((int)(puVar8 + 3) - uVar12) >> uVar12 * 8;
        uVar1 = (int)puVar13 + 7U & 7;
        puVar3 = (ulong *)(((int)puVar13 + 7U) - uVar1);
        *puVar3 = *puVar3 & -1L << (uVar1 + 1) * 8 | param_8 >> (7 - uVar1) * 8;
        uVar1 = (uint)puVar13 & 7;
        *(ulong *)((int)puVar13 - uVar1) =
             param_8 << uVar1 * 8 |
             *(ulong *)((int)puVar13 - uVar1) & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        uVar1 = (int)puVar13 + 0xfU & 7;
        puVar3 = (ulong *)(((int)puVar13 + 0xfU) - uVar1);
        *puVar3 = *puVar3 & -1L << (uVar1 + 1) * 8 | param_3 >> (7 - uVar1) * 8;
        uVar1 = (uint)(puVar13 + 1) & 7;
        puVar3 = (ulong *)((int)(puVar13 + 1) - uVar1);
        *puVar3 = param_3 << uVar1 * 8 | *puVar3 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        uVar1 = (int)puVar13 + 0x17U & 7;
        puVar3 = (ulong *)(((int)puVar13 + 0x17U) - uVar1);
        *puVar3 = *puVar3 & -1L << (uVar1 + 1) * 8 | uVar16 >> (7 - uVar1) * 8;
        uVar1 = (uint)(puVar13 + 2) & 7;
        puVar3 = (ulong *)((int)(puVar13 + 2) - uVar1);
        *puVar3 = uVar16 << uVar1 * 8 | *puVar3 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        uVar1 = (int)puVar13 + 0x1fU & 7;
        puVar3 = (ulong *)(((int)puVar13 + 0x1fU) - uVar1);
        *puVar3 = *puVar3 & -1L << (uVar1 + 1) * 8 | param_5 >> (7 - uVar1) * 8;
        uVar1 = (uint)(puVar13 + 3) & 7;
        puVar3 = (ulong *)((int)(puVar13 + 3) - uVar1);
        *puVar3 = param_5 << uVar1 * 8 | *puVar3 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        puVar8 = puVar8 + 4;
        puVar13 = puVar13 + 4;
      } while (puVar8 != puVar5);
    }
    uVar1 = (int)puVar8 + 7U & 7;
    uVar12 = (uint)puVar8 & 7;
    uVar6 = (*(long *)(((int)puVar8 + 7U) - uVar1) << (7 - uVar1) * 8 |
            uVar16 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
            *(ulong *)((int)puVar8 - uVar12) >> uVar12 * 8;
    uVar1 = (int)puVar8 + 0xfU & 7;
    uVar12 = (uint)(puVar8 + 1) & 7;
    uVar10 = (*(long *)(((int)puVar8 + 0xfU) - uVar1) << (7 - uVar1) * 8 |
             param_5 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
             *(ulong *)((int)(puVar8 + 1) - uVar12) >> uVar12 * 8;
    uVar1 = (int)puVar8 + 0x17U & 7;
    uVar12 = (uint)(puVar8 + 2) & 7;
    uVar19 = (*(long *)(((int)puVar8 + 0x17U) - uVar1) << (7 - uVar1) * 8 |
             param_6 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
             *(ulong *)((int)(puVar8 + 2) - uVar12) >> uVar12 * 8;
    uVar16 = puVar8[3];
    uVar1 = (int)puVar13 + 7U & 7;
    puVar8 = (ulong *)(((int)puVar13 + 7U) - uVar1);
    *puVar8 = *puVar8 & -1L << (uVar1 + 1) * 8 | uVar6 >> (7 - uVar1) * 8;
    uVar1 = (uint)puVar13 & 7;
    *(ulong *)((int)puVar13 - uVar1) =
         uVar6 << uVar1 * 8 |
         *(ulong *)((int)puVar13 - uVar1) & 0xffffffffffffffffU >> (8 - uVar1) * 8;
    uVar1 = (int)puVar13 + 0xfU & 7;
    puVar8 = (ulong *)(((int)puVar13 + 0xfU) - uVar1);
    *puVar8 = *puVar8 & -1L << (uVar1 + 1) * 8 | uVar10 >> (7 - uVar1) * 8;
    uVar1 = (uint)(puVar13 + 1) & 7;
    puVar8 = (ulong *)((int)(puVar13 + 1) - uVar1);
    *puVar8 = uVar10 << uVar1 * 8 | *puVar8 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
    uVar1 = (int)puVar13 + 0x17U & 7;
    puVar8 = (ulong *)(((int)puVar13 + 0x17U) - uVar1);
    *puVar8 = *puVar8 & -1L << (uVar1 + 1) * 8 | uVar19 >> (7 - uVar1) * 8;
    uVar1 = (uint)(puVar13 + 2) & 7;
    puVar8 = (ulong *)((int)(puVar13 + 2) - uVar1);
    *puVar8 = uVar19 << uVar1 * 8 | *puVar8 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
    *(int *)(puVar13 + 3) = (int)uVar16;
    break;
  case 4:
    if (uVar16 == 0) {
      iVar15 = *(int *)(param_2 + 4);
      goto LAB_00144488;
    }
    puVar11 = *(undefined8 **)(iVar15 + 4);
    puVar9 = *(undefined8 **)(param_2 + 4);
    puVar4 = puVar11 + 0x24;
    if ((((uint)puVar11 | (uint)puVar9) & 7) == 0) {
      do {
        uVar17 = puVar11[1];
        uVar18 = puVar11[2];
        uVar14 = puVar11[3];
        *puVar9 = *puVar11;
        puVar9[1] = uVar17;
        puVar9[2] = uVar18;
        puVar9[3] = uVar14;
        puVar11 = puVar11 + 4;
        puVar9 = puVar9 + 4;
      } while (puVar11 != puVar4);
    }
    else {
      do {
        uVar1 = (int)puVar11 + 7U & 7;
        uVar12 = (uint)puVar11 & 7;
        param_8 = (*(long *)(((int)puVar11 + 7U) - uVar1) << (7 - uVar1) * 8 |
                  param_8 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                  *(ulong *)((int)puVar11 - uVar12) >> uVar12 * 8;
        uVar1 = (int)puVar11 + 0xfU & 7;
        uVar12 = (uint)(puVar11 + 1) & 7;
        param_3 = (*(long *)(((int)puVar11 + 0xfU) - uVar1) << (7 - uVar1) * 8 |
                  param_3 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                  *(ulong *)((int)(puVar11 + 1) - uVar12) >> uVar12 * 8;
        uVar1 = (int)puVar11 + 0x17U & 7;
        uVar12 = (uint)(puVar11 + 2) & 7;
        uVar16 = (*(long *)(((int)puVar11 + 0x17U) - uVar1) << (7 - uVar1) * 8 |
                 uVar16 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                 *(ulong *)((int)(puVar11 + 2) - uVar12) >> uVar12 * 8;
        uVar1 = (int)puVar11 + 0x1fU & 7;
        uVar12 = (uint)(puVar11 + 3) & 7;
        param_5 = (*(long *)(((int)puVar11 + 0x1fU) - uVar1) << (7 - uVar1) * 8 |
                  param_5 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                  *(ulong *)((int)(puVar11 + 3) - uVar12) >> uVar12 * 8;
        uVar1 = (int)puVar9 + 7U & 7;
        puVar8 = (ulong *)(((int)puVar9 + 7U) - uVar1);
        *puVar8 = *puVar8 & -1L << (uVar1 + 1) * 8 | param_8 >> (7 - uVar1) * 8;
        uVar1 = (uint)puVar9 & 7;
        *(ulong *)((int)puVar9 - uVar1) =
             param_8 << uVar1 * 8 |
             *(ulong *)((int)puVar9 - uVar1) & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        uVar1 = (int)puVar9 + 0xfU & 7;
        puVar8 = (ulong *)(((int)puVar9 + 0xfU) - uVar1);
        *puVar8 = *puVar8 & -1L << (uVar1 + 1) * 8 | param_3 >> (7 - uVar1) * 8;
        uVar1 = (uint)(puVar9 + 1) & 7;
        puVar8 = (ulong *)((int)(puVar9 + 1) - uVar1);
        *puVar8 = param_3 << uVar1 * 8 | *puVar8 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        uVar1 = (int)puVar9 + 0x17U & 7;
        puVar8 = (ulong *)(((int)puVar9 + 0x17U) - uVar1);
        *puVar8 = *puVar8 & -1L << (uVar1 + 1) * 8 | uVar16 >> (7 - uVar1) * 8;
        uVar1 = (uint)(puVar9 + 2) & 7;
        puVar8 = (ulong *)((int)(puVar9 + 2) - uVar1);
        *puVar8 = uVar16 << uVar1 * 8 | *puVar8 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        uVar1 = (int)puVar9 + 0x1fU & 7;
        puVar8 = (ulong *)(((int)puVar9 + 0x1fU) - uVar1);
        *puVar8 = *puVar8 & -1L << (uVar1 + 1) * 8 | param_5 >> (7 - uVar1) * 8;
        uVar1 = (uint)(puVar9 + 3) & 7;
        puVar8 = (ulong *)((int)(puVar9 + 3) - uVar1);
        *puVar8 = param_5 << uVar1 * 8 | *puVar8 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        puVar11 = puVar11 + 4;
        puVar9 = puVar9 + 4;
      } while (puVar11 != puVar4);
    }
    uVar1 = (int)puVar11 + 7U & 7;
    uVar12 = (uint)puVar11 & 7;
    uVar16 = (*(long *)(((int)puVar11 + 7U) - uVar1) << (7 - uVar1) * 8 |
             uVar16 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
             *(ulong *)((int)puVar11 - uVar12) >> uVar12 * 8;
    uVar1 = (int)puVar11 + 0xfU & 7;
    uVar12 = (uint)(puVar11 + 1) & 7;
    uVar6 = (*(long *)(((int)puVar11 + 0xfU) - uVar1) << (7 - uVar1) * 8 |
            param_5 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
            *(ulong *)((int)(puVar11 + 1) - uVar12) >> uVar12 * 8;
    uVar1 = (int)puVar9 + 7U & 7;
    puVar8 = (ulong *)(((int)puVar9 + 7U) - uVar1);
    *puVar8 = *puVar8 & -1L << (uVar1 + 1) * 8 | uVar16 >> (7 - uVar1) * 8;
    uVar1 = (uint)puVar9 & 7;
    *(ulong *)((int)puVar9 - uVar1) =
         uVar16 << uVar1 * 8 |
         *(ulong *)((int)puVar9 - uVar1) & 0xffffffffffffffffU >> (8 - uVar1) * 8;
    uVar1 = (int)puVar9 + 0xfU & 7;
    puVar8 = (ulong *)(((int)puVar9 + 0xfU) - uVar1);
    *puVar8 = *puVar8 & -1L << (uVar1 + 1) * 8 | uVar6 >> (7 - uVar1) * 8;
    uVar1 = (uint)(puVar9 + 1) & 7;
    puVar8 = (ulong *)((int)(puVar9 + 1) - uVar1);
    *puVar8 = uVar6 << uVar1 * 8 | *puVar8 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
    break;
  case 5:
    if (uVar16 == 0) {
      iVar15 = *(int *)(param_2 + 4);
      goto LAB_00144488;
    }
    puVar9 = *(undefined8 **)(iVar15 + 4);
    puVar11 = *(undefined8 **)(param_2 + 4);
    puVar4 = puVar9 + 0x28;
    if ((((uint)puVar9 | (uint)puVar11) & 7) == 0) {
      do {
        uVar17 = puVar9[1];
        uVar18 = puVar9[2];
        uVar14 = puVar9[3];
        *puVar11 = *puVar9;
        puVar11[1] = uVar17;
        puVar11[2] = uVar18;
        puVar11[3] = uVar14;
        puVar9 = puVar9 + 4;
        puVar11 = puVar11 + 4;
      } while (puVar9 != puVar4);
    }
    else {
      do {
        uVar1 = (int)puVar9 + 7U & 7;
        uVar12 = (uint)puVar9 & 7;
        param_8 = (*(long *)(((int)puVar9 + 7U) - uVar1) << (7 - uVar1) * 8 |
                  param_8 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                  *(ulong *)((int)puVar9 - uVar12) >> uVar12 * 8;
        uVar1 = (int)puVar9 + 0xfU & 7;
        uVar12 = (uint)(puVar9 + 1) & 7;
        param_3 = (*(long *)(((int)puVar9 + 0xfU) - uVar1) << (7 - uVar1) * 8 |
                  param_3 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                  *(ulong *)((int)(puVar9 + 1) - uVar12) >> uVar12 * 8;
        uVar1 = (int)puVar9 + 0x17U & 7;
        uVar12 = (uint)(puVar9 + 2) & 7;
        uVar16 = (*(long *)(((int)puVar9 + 0x17U) - uVar1) << (7 - uVar1) * 8 |
                 uVar16 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                 *(ulong *)((int)(puVar9 + 2) - uVar12) >> uVar12 * 8;
        uVar1 = (int)puVar9 + 0x1fU & 7;
        uVar12 = (uint)(puVar9 + 3) & 7;
        param_5 = (*(long *)(((int)puVar9 + 0x1fU) - uVar1) << (7 - uVar1) * 8 |
                  param_5 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                  *(ulong *)((int)(puVar9 + 3) - uVar12) >> uVar12 * 8;
        uVar1 = (int)puVar11 + 7U & 7;
        puVar8 = (ulong *)(((int)puVar11 + 7U) - uVar1);
        *puVar8 = *puVar8 & -1L << (uVar1 + 1) * 8 | param_8 >> (7 - uVar1) * 8;
        uVar1 = (uint)puVar11 & 7;
        *(ulong *)((int)puVar11 - uVar1) =
             param_8 << uVar1 * 8 |
             *(ulong *)((int)puVar11 - uVar1) & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        uVar1 = (int)puVar11 + 0xfU & 7;
        puVar8 = (ulong *)(((int)puVar11 + 0xfU) - uVar1);
        *puVar8 = *puVar8 & -1L << (uVar1 + 1) * 8 | param_3 >> (7 - uVar1) * 8;
        uVar1 = (uint)(puVar11 + 1) & 7;
        puVar8 = (ulong *)((int)(puVar11 + 1) - uVar1);
        *puVar8 = param_3 << uVar1 * 8 | *puVar8 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        uVar1 = (int)puVar11 + 0x17U & 7;
        puVar8 = (ulong *)(((int)puVar11 + 0x17U) - uVar1);
        *puVar8 = *puVar8 & -1L << (uVar1 + 1) * 8 | uVar16 >> (7 - uVar1) * 8;
        uVar1 = (uint)(puVar11 + 2) & 7;
        puVar8 = (ulong *)((int)(puVar11 + 2) - uVar1);
        *puVar8 = uVar16 << uVar1 * 8 | *puVar8 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        uVar1 = (int)puVar11 + 0x1fU & 7;
        puVar8 = (ulong *)(((int)puVar11 + 0x1fU) - uVar1);
        *puVar8 = *puVar8 & -1L << (uVar1 + 1) * 8 | param_5 >> (7 - uVar1) * 8;
        uVar1 = (uint)(puVar11 + 3) & 7;
        puVar8 = (ulong *)((int)(puVar11 + 3) - uVar1);
        *puVar8 = param_5 << uVar1 * 8 | *puVar8 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        puVar9 = puVar9 + 4;
        puVar11 = puVar11 + 4;
      } while (puVar9 != puVar4);
    }
    goto LAB_001442b4;
  case 6:
    if (uVar16 == 0) {
      iVar15 = *(int *)(param_2 + 4);
      goto LAB_00144488;
    }
    puVar13 = *(ulong **)(iVar15 + 4);
    puVar8 = *(ulong **)(param_2 + 4);
    puVar5 = puVar13 + 0x30;
    if ((((uint)puVar13 | (uint)puVar8) & 7) == 0) {
      do {
        param_6 = *puVar13;
        uVar10 = puVar13[1];
        uVar19 = puVar13[2];
        uVar6 = puVar13[3];
        *puVar8 = param_6;
        puVar8[1] = uVar10;
        puVar8[2] = uVar19;
        puVar8[3] = uVar6;
        puVar13 = puVar13 + 4;
        puVar8 = puVar8 + 4;
      } while (puVar13 != puVar5);
    }
    else {
      do {
        uVar1 = (int)puVar13 + 7U & 7;
        uVar12 = (uint)puVar13 & 7;
        param_8 = (*(long *)(((int)puVar13 + 7U) - uVar1) << (7 - uVar1) * 8 |
                  param_8 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                  *(ulong *)((int)puVar13 - uVar12) >> uVar12 * 8;
        uVar1 = (int)puVar13 + 0xfU & 7;
        uVar12 = (uint)(puVar13 + 1) & 7;
        param_3 = (*(long *)(((int)puVar13 + 0xfU) - uVar1) << (7 - uVar1) * 8 |
                  param_3 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                  *(ulong *)((int)(puVar13 + 1) - uVar12) >> uVar12 * 8;
        uVar1 = (int)puVar13 + 0x17U & 7;
        uVar12 = (uint)(puVar13 + 2) & 7;
        uVar16 = (*(long *)(((int)puVar13 + 0x17U) - uVar1) << (7 - uVar1) * 8 |
                 uVar16 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                 *(ulong *)((int)(puVar13 + 2) - uVar12) >> uVar12 * 8;
        uVar1 = (int)puVar13 + 0x1fU & 7;
        uVar12 = (uint)(puVar13 + 3) & 7;
        param_5 = (*(long *)(((int)puVar13 + 0x1fU) - uVar1) << (7 - uVar1) * 8 |
                  param_5 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                  *(ulong *)((int)(puVar13 + 3) - uVar12) >> uVar12 * 8;
        uVar1 = (int)puVar8 + 7U & 7;
        puVar3 = (ulong *)(((int)puVar8 + 7U) - uVar1);
        *puVar3 = *puVar3 & -1L << (uVar1 + 1) * 8 | param_8 >> (7 - uVar1) * 8;
        uVar1 = (uint)puVar8 & 7;
        *(ulong *)((int)puVar8 - uVar1) =
             param_8 << uVar1 * 8 |
             *(ulong *)((int)puVar8 - uVar1) & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        uVar1 = (int)puVar8 + 0xfU & 7;
        puVar3 = (ulong *)(((int)puVar8 + 0xfU) - uVar1);
        *puVar3 = *puVar3 & -1L << (uVar1 + 1) * 8 | param_3 >> (7 - uVar1) * 8;
        uVar1 = (uint)(puVar8 + 1) & 7;
        puVar3 = (ulong *)((int)(puVar8 + 1) - uVar1);
        *puVar3 = param_3 << uVar1 * 8 | *puVar3 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        uVar1 = (int)puVar8 + 0x17U & 7;
        puVar3 = (ulong *)(((int)puVar8 + 0x17U) - uVar1);
        *puVar3 = *puVar3 & -1L << (uVar1 + 1) * 8 | uVar16 >> (7 - uVar1) * 8;
        uVar1 = (uint)(puVar8 + 2) & 7;
        puVar3 = (ulong *)((int)(puVar8 + 2) - uVar1);
        *puVar3 = uVar16 << uVar1 * 8 | *puVar3 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        uVar1 = (int)puVar8 + 0x1fU & 7;
        puVar3 = (ulong *)(((int)puVar8 + 0x1fU) - uVar1);
        *puVar3 = *puVar3 & -1L << (uVar1 + 1) * 8 | param_5 >> (7 - uVar1) * 8;
        uVar1 = (uint)(puVar8 + 3) & 7;
        puVar3 = (ulong *)((int)(puVar8 + 3) - uVar1);
        *puVar3 = param_5 << uVar1 * 8 | *puVar3 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        puVar13 = puVar13 + 4;
        puVar8 = puVar8 + 4;
      } while (puVar13 != puVar5);
    }
    goto LAB_00144454;
  case 7:
    if (uVar16 == 0) {
      iVar15 = *(int *)(param_2 + 4);
      goto LAB_00144488;
    }
    puVar13 = *(ulong **)(iVar15 + 4);
    puVar8 = *(ulong **)(param_2 + 4);
    puVar5 = puVar13 + 0x30;
    if ((((uint)puVar13 | (uint)puVar8) & 7) == 0) {
      do {
        param_6 = *puVar13;
        uVar10 = puVar13[1];
        uVar19 = puVar13[2];
        uVar6 = puVar13[3];
        *puVar8 = param_6;
        puVar8[1] = uVar10;
        puVar8[2] = uVar19;
        puVar8[3] = uVar6;
        puVar13 = puVar13 + 4;
        puVar8 = puVar8 + 4;
      } while (puVar13 != puVar5);
    }
    else {
      do {
        uVar1 = (int)puVar13 + 7U & 7;
        uVar12 = (uint)puVar13 & 7;
        param_8 = (*(long *)(((int)puVar13 + 7U) - uVar1) << (7 - uVar1) * 8 |
                  param_8 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                  *(ulong *)((int)puVar13 - uVar12) >> uVar12 * 8;
        uVar1 = (int)puVar13 + 0xfU & 7;
        uVar12 = (uint)(puVar13 + 1) & 7;
        param_3 = (*(long *)(((int)puVar13 + 0xfU) - uVar1) << (7 - uVar1) * 8 |
                  param_3 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                  *(ulong *)((int)(puVar13 + 1) - uVar12) >> uVar12 * 8;
        uVar1 = (int)puVar13 + 0x17U & 7;
        uVar12 = (uint)(puVar13 + 2) & 7;
        uVar16 = (*(long *)(((int)puVar13 + 0x17U) - uVar1) << (7 - uVar1) * 8 |
                 uVar16 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                 *(ulong *)((int)(puVar13 + 2) - uVar12) >> uVar12 * 8;
        uVar1 = (int)puVar13 + 0x1fU & 7;
        uVar12 = (uint)(puVar13 + 3) & 7;
        param_5 = (*(long *)(((int)puVar13 + 0x1fU) - uVar1) << (7 - uVar1) * 8 |
                  param_5 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
                  *(ulong *)((int)(puVar13 + 3) - uVar12) >> uVar12 * 8;
        uVar1 = (int)puVar8 + 7U & 7;
        puVar3 = (ulong *)(((int)puVar8 + 7U) - uVar1);
        *puVar3 = *puVar3 & -1L << (uVar1 + 1) * 8 | param_8 >> (7 - uVar1) * 8;
        uVar1 = (uint)puVar8 & 7;
        *(ulong *)((int)puVar8 - uVar1) =
             param_8 << uVar1 * 8 |
             *(ulong *)((int)puVar8 - uVar1) & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        uVar1 = (int)puVar8 + 0xfU & 7;
        puVar3 = (ulong *)(((int)puVar8 + 0xfU) - uVar1);
        *puVar3 = *puVar3 & -1L << (uVar1 + 1) * 8 | param_3 >> (7 - uVar1) * 8;
        uVar1 = (uint)(puVar8 + 1) & 7;
        puVar3 = (ulong *)((int)(puVar8 + 1) - uVar1);
        *puVar3 = param_3 << uVar1 * 8 | *puVar3 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        uVar1 = (int)puVar8 + 0x17U & 7;
        puVar3 = (ulong *)(((int)puVar8 + 0x17U) - uVar1);
        *puVar3 = *puVar3 & -1L << (uVar1 + 1) * 8 | uVar16 >> (7 - uVar1) * 8;
        uVar1 = (uint)(puVar8 + 2) & 7;
        puVar3 = (ulong *)((int)(puVar8 + 2) - uVar1);
        *puVar3 = uVar16 << uVar1 * 8 | *puVar3 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        uVar1 = (int)puVar8 + 0x1fU & 7;
        puVar3 = (ulong *)(((int)puVar8 + 0x1fU) - uVar1);
        *puVar3 = *puVar3 & -1L << (uVar1 + 1) * 8 | param_5 >> (7 - uVar1) * 8;
        uVar1 = (uint)(puVar8 + 3) & 7;
        puVar3 = (ulong *)((int)(puVar8 + 3) - uVar1);
        *puVar3 = param_5 << uVar1 * 8 | *puVar3 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
        puVar13 = puVar13 + 4;
        puVar8 = puVar8 + 4;
      } while (puVar13 != puVar5);
    }
LAB_00144454:
    uVar1 = (int)puVar13 + 7U & 7;
    uVar12 = (uint)puVar13 & 7;
    uVar16 = (*(long *)(((int)puVar13 + 7U) - uVar1) << (7 - uVar1) * 8 |
             uVar16 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
             *(ulong *)((int)puVar13 - uVar12) >> uVar12 * 8;
    uVar1 = (int)puVar13 + 0xfU & 7;
    uVar12 = (uint)(puVar13 + 1) & 7;
    uVar6 = (*(long *)(((int)puVar13 + 0xfU) - uVar1) << (7 - uVar1) * 8 |
            param_5 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
            *(ulong *)((int)(puVar13 + 1) - uVar12) >> uVar12 * 8;
    uVar1 = (int)puVar13 + 0x17U & 7;
    uVar12 = (uint)(puVar13 + 2) & 7;
    uVar10 = (*(long *)(((int)puVar13 + 0x17U) - uVar1) << (7 - uVar1) * 8 |
             param_6 & 0xffffffffffffffffU >> (uVar1 + 1) * 8) & -1L << (8 - uVar12) * 8 |
             *(ulong *)((int)(puVar13 + 2) - uVar12) >> uVar12 * 8;
    uVar1 = (int)puVar8 + 7U & 7;
    puVar13 = (ulong *)(((int)puVar8 + 7U) - uVar1);
    *puVar13 = *puVar13 & -1L << (uVar1 + 1) * 8 | uVar16 >> (7 - uVar1) * 8;
    uVar1 = (uint)puVar8 & 7;
    *(ulong *)((int)puVar8 - uVar1) =
         uVar16 << uVar1 * 8 |
         *(ulong *)((int)puVar8 - uVar1) & 0xffffffffffffffffU >> (8 - uVar1) * 8;
    uVar1 = (int)puVar8 + 0xfU & 7;
    puVar13 = (ulong *)(((int)puVar8 + 0xfU) - uVar1);
    *puVar13 = *puVar13 & -1L << (uVar1 + 1) * 8 | uVar6 >> (7 - uVar1) * 8;
    uVar1 = (uint)(puVar8 + 1) & 7;
    puVar13 = (ulong *)((int)(puVar8 + 1) - uVar1);
    *puVar13 = uVar6 << uVar1 * 8 | *puVar13 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
    uVar1 = (int)puVar8 + 0x17U & 7;
    puVar13 = (ulong *)(((int)puVar8 + 0x17U) - uVar1);
    *puVar13 = *puVar13 & -1L << (uVar1 + 1) * 8 | uVar10 >> (7 - uVar1) * 8;
    uVar1 = (uint)(puVar8 + 2) & 7;
    puVar8 = (ulong *)((int)(puVar8 + 2) - uVar1);
    *puVar8 = uVar10 << uVar1 * 8 | *puVar8 & 0xffffffffffffffffU >> (8 - uVar1) * 8;
    break;
  default:
    iVar15 = *(int *)(param_2 + 4);
    goto LAB_00144488;
  }
  iVar15 = *(int *)(param_2 + 4);
LAB_00144488:
  *(undefined4 *)(iVar15 + 0x94) = 0;
  *(undefined4 *)(*(int *)(param_2 + 4) + 0x98) = 0;
  *(undefined4 *)(*(int *)(param_2 + 4) + 0x9c) = 0;
  *(undefined4 *)(*(int *)(param_2 + 4) + 0xa0) = 0;
  *(undefined1 *)(*(int *)(param_2 + 4) + 0xa7) = 0;
  *(undefined1 *)(*(int *)(param_2 + 4) + 0xa8) = 0;
  *(undefined1 *)(*(int *)(param_2 + 4) + 0xa9) = 0;
  *(undefined4 *)(*(int *)(param_2 + 4) + 0xec) = 0;
  *(undefined4 *)(*(int *)(param_2 + 4) + 0xf4) = 0;
  *(undefined4 *)(*(int *)(param_2 + 4) + 0xf0) = 0;
  *(undefined4 *)(*(int *)(param_2 + 4) + 0xf8) = 0;
  *(undefined4 *)(*(int *)(param_2 + 4) + 0xfc) = 0;
  *(undefined4 *)(*(int *)(param_2 + 4) + 0x100) = 0;
  *(undefined4 *)(*(int *)(param_2 + 4) + 0x90) = 0;
  return;
}

