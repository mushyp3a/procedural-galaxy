{
  description = "Procedural universe generator";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
    in {
      devShells.${system}.default = pkgs.mkShell {
        packages = with pkgs; [
          python3
          python3Packages.noise
          python3Packages.plotly
          python3Packages.black
          python3Packages.numpy
        ];
      };
    };
}
