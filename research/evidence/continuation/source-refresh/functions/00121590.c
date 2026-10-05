
/* source file (direct reference to its __FILE__ string, not proof of authorship):
   ../modules4/3d/3dconstr.c:217 */

long FUN_00121590(long param_1,long param_2,int *param_3)

{
  short sVar1;
  int iVar2;
  long lVar3;
  uint uVar4;
  int iVar5;
  undefined4 *puVar6;
  undefined4 *puVar7;
  undefined4 *puVar8;
  
  if (param_1 != -1) {
    iVar2 = FUN_001213d8();
    uVar4 = 0;
    iVar5 = 0;
    if (-1 < *(int *)(iVar2 + 0x14)) {
      uVar4 = (uint)*(byte *)(iVar2 + 0x16);
      iVar5 = (int)*(short *)(iVar2 + 10) - (uint)*(byte *)(iVar2 + 0x16);
    }
    sVar1 = *(short *)(iVar2 + 0xc);
    iVar5 = uVar4 * 0x40 + 0x90 + iVar5 * 0x10 + (uint)*(byte *)(iVar2 + 0xf) * 4;
    if (*(short *)(iVar2 + 0xc) != 0) {
      iVar5 = iVar5 + *(short *)(iVar2 + 0xc) * 0x40 + 0x40;
    }
    *param_3 = iVar5;
    lVar3 = 0;
    if (param_2 != 0) {
      puVar6 = (undefined4 *)param_2;
      *(ulong *)(puVar6 + 0x18) =
           *(ulong *)(puVar6 + 0x18) & 0xffffffffffc03fff | (ulong)*(byte *)(iVar2 + 0xf) << 0xe;
      puVar8 = puVar6 + 0x24;
      puVar7 = puVar8;
      if (*(char *)(iVar2 + 0xf) != '\0') {
        puVar6[0x1e] = puVar8;
        puVar7 = puVar8 + *(byte *)(iVar2 + 0xf);
        FUN_0020c7fc(puVar8,0,(uint)*(byte *)(iVar2 + 0xf) * 4);
        sVar1 = *(short *)(iVar2 + 0xc);
      }
      iVar5 = (int)sVar1;
      puVar8 = puVar7;
      if (iVar5 != 0) {
        puVar6[0x1f] = puVar7;
        puVar8 = puVar7 + iVar5 * 0x10 + 0x10;
        FUN_0020c7fc(puVar7,0,iVar5 * 0x40 + 0x40);
      }
      puRam0028f138 = (undefined4 *)0x0;
      if ((*(short *)(iVar2 + 10) != 0) &&
         (puRam0028f138 = (undefined4 *)0x0, (*(uint *)(iVar2 + 0x14) & 0x80000000) == 0)) {
        puRam0028f138 = puVar8;
      }
      puVar6[1] = (uint)param_1;
      *puVar6 = 0;
      puVar7 = puRam0028f138;
      if (*(char *)(iVar2 + 0x11) == '\0') {
        puVar6[0x1b] = 0;
      }
      else if ((*(uint *)(iVar2 + 0x14) & 0x80000000) == 0) {
        puVar6[0x1b] = puRam0028f138;
        puRam0028f138 =
             puRam0028f138 + (uint)*(byte *)(iVar2 + 0x14) * 0xc + (uint)*(byte *)(iVar2 + 0x11) * 4
        ;
        FUN_001217f8(param_2,puVar7,*(undefined4 *)(iVar2 + 0x54));
      }
      else {
        puVar6[0x1b] = 0;
      }
      puRam0028f138 = (undefined4 *)0x0;
      FUN_00113aa8(0,0,0,0,0,0,puVar6 + 4);
      *(ulong *)(puVar6 + 0x18) = *(ulong *)(puVar6 + 0x18) & 0xffffffffffbfffc1 | 0x3fc1;
      puVar6[0x19] = (uint)param_1 & 0xffff0000;
      puVar6[0x20] = 0;
      puVar6[0x1a] = 0;
      puVar6[0x1c] = 0;
      puVar6[0x1d] = 0;
      lVar3 = param_2;
    }
    return lVar3;
  }
                    /* WARNING: Subroutine does not return */
  FUN_00105888(0x2528a8,0xd9,0x2528c8);
}

